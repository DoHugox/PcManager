"""
VNServerSentinel - Safe Auto-Updater with Watchdog Rollback
Pulls releases from GitHub, stages updates, and rolls back automatically
if the new version fails to establish network/Telegram connection within 60s.
"""

import os
import sys
import json
import shutil
import logging
import zipfile
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any

from config import Config

logger = logging.getLogger("VNServerSentinel.Updater")

CURRENT_VERSION = "1.0.0"
VERSION_FILE = Config.BASE_DIR / "VERSION"
UPDATE_FLAG = Config.DATA_DIR / "update_pending.flag"

def get_current_version() -> str:
    """Read version from VERSION file or fallback to default."""
    if VERSION_FILE.exists():
        try:
            return VERSION_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return CURRENT_VERSION

def check_github_update() -> tuple[bool, Optional[str], Optional[str], str]:
    """
    Check GitHub Releases for a newer version.
    Returns (has_update, new_version, download_url, release_notes)
    """
    repo = Config.GITHUB_REPO
    if not repo or repo == "owner/VNServerSentinel":
        return False, None, None, "Chưa cấu hình GITHUB_REPO hợp lệ trong .env."

    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "VNServerSentinel-Updater",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            latest_tag = data.get("tag_name", "").lstrip("v").strip()
            release_notes = data.get("body", "Không có ghi chú phiên bản.")
            assets = data.get("assets", [])

            curr_ver = get_current_version().lstrip("v").strip()
            if latest_tag and latest_tag != curr_ver:
                # Find zip asset or default zipball
                download_url = None
                for asset in assets:
                    if asset.get("name", "").endswith(".zip"):
                        download_url = asset.get("browser_download_url")
                        break
                if not download_url:
                    download_url = data.get("zipball_url")

                return True, latest_tag, download_url, release_notes
            return False, curr_ver, None, "Bạn đang ở phiên bản mới nhất."
    except Exception as e:
        logger.error(f"Error checking GitHub update: {e}")
        return False, None, None, f"Lỗi kiểm tra cập nhật: {e}"

def backup_current_installation():
    """Backup current source code files to backup folder before updating."""
    Config.ensure_directories()
    # Clean old backup
    if Config.BACKUP_DIR.exists():
        shutil.rmtree(Config.BACKUP_DIR)
    Config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Copy files excluding data, venv, git
    for item in Config.BASE_DIR.iterdir():
        if item.name in ("data", ".git", ".venv", "venv", "__pycache__", "staging", ".env"):
            continue
        dest = Config.BACKUP_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    logger.info("Backup of current version completed successfully.")

def apply_update_from_zip(zip_path: Path, new_version: str) -> tuple[bool, str]:
    """
    Extracts update zip, replaces source files, sets watchdog flag.
    Excludes .env and data directory to protect user config.
    """
    try:
        backup_current_installation()

        # Extract to staging
        if Config.STAGING_DIR.exists():
            shutil.rmtree(Config.STAGING_DIR)
        Config.STAGING_DIR.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(Config.STAGING_DIR)

        # Locate root directory inside zip if it was nested
        extracted_root = Config.STAGING_DIR
        subdirs = [p for p in Config.STAGING_DIR.iterdir() if p.is_dir()]
        if len(subdirs) == 1 and not (Config.STAGING_DIR / "main.py").exists():
            extracted_root = subdirs[0]

        # Copy new files into BASE_DIR
        for item in extracted_root.iterdir():
            if item.name in (".env", "data", "state.json"):
                continue # Never overwrite user credentials or local state
            dest = Config.BASE_DIR / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        # Update version file
        VERSION_FILE.write_text(new_version, encoding="utf-8")

        # Create Watchdog Flag
        UPDATE_FLAG.write_text(json.dumps({
            "version": new_version,
            "timestamp": str(Path.ctime(VERSION_FILE))
        }), encoding="utf-8")

        return True, f"Đã áp dụng bản cập nhật v{new_version}. Khởi động lại dịch vụ..."

    except Exception as e:
        logger.error(f"Failed to apply update: {e}")
        rollback_to_backup()
        return False, f"Lỗi cập nhật: {e}. Đã tự động rollback về bản cũ!"

def rollback_to_backup() -> bool:
    """Restores previously backed up files if the update crashes."""
    logger.warning("Initiating rollback to previous version...")
    if not Config.BACKUP_DIR.exists():
        logger.error("No backup found to rollback!")
        return False

    try:
        for item in Config.BACKUP_DIR.iterdir():
            dest = Config.BASE_DIR / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        if UPDATE_FLAG.exists():
            UPDATE_FLAG.unlink()

        logger.info("Rollback completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Critical error during rollback: {e}")
        return False

def check_and_clear_update_flag() -> Optional[str]:
    """Called after startup to confirm the new version is healthy and clear flag."""
    if UPDATE_FLAG.exists():
        try:
            data = json.loads(UPDATE_FLAG.read_text(encoding="utf-8"))
            ver = data.get("version", "mới")
            UPDATE_FLAG.unlink()
            return ver
        except Exception:
            if UPDATE_FLAG.exists():
                UPDATE_FLAG.unlink()
    return None
