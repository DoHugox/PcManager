"""
VNServerSentinel - Remote File & Folder Manager
Provides elevated administrator capabilities to browse, read,
upload, and download files directly via Telegram.
"""

import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("VNServerSentinel.FileManager")

def format_file_size(size_bytes: int) -> str:
    """Format bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:3.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def get_drives_or_roots() -> List[str]:
    """Get available drive letters on Windows or root on Unix."""
    if os.name == 'nt':
        import string
        from ctypes import windll
        drives = []
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(f"{letter}:\\")
            bitmask >>= 1
        return drives or ["C:\\"]
    return ["/"]

def list_directory(target_path: Optional[str] = None) -> tuple[bool, Dict[str, Any], str]:
    """
    List contents of directory. If target_path is None or empty,
    returns current working directory or drive list.
    """
    try:
        if not target_path or target_path.strip() == "":
            path_obj = Path.cwd()
        else:
            path_obj = Path(target_path).resolve()

        if not path_obj.exists():
            return False, {}, f"Đường dẫn không tồn tại: `{target_path}`"

        if not path_obj.is_dir():
            return False, {}, f"`{target_path}` là tệp tin, không phải thư mục."

        items = []
        # Add parent directory indicator
        if path_obj.parent != path_obj:
            items.append({
                "name": ".. (Thư mục cha)",
                "path": str(path_obj.parent),
                "is_dir": True,
                "size": "-",
                "mtime": "-"
            })

        # Scan files and directories
        for entry in sorted(path_obj.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            try:
                stat = entry.stat()
                mtime_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                if entry.is_dir():
                    items.append({
                        "name": f"📁 {entry.name}/",
                        "path": str(entry),
                        "is_dir": True,
                        "size": "-",
                        "mtime": mtime_str
                    })
                else:
                    items.append({
                        "name": f"📄 {entry.name}",
                        "path": str(entry),
                        "is_dir": False,
                        "size": format_file_size(stat.st_size),
                        "mtime": mtime_str
                    })
            except (PermissionError, FileNotFoundError):
                items.append({
                    "name": f"🔒 {entry.name} (Không có quyền truy cập)",
                    "path": str(entry),
                    "is_dir": entry.is_dir(),
                    "size": "-",
                    "mtime": "-"
                })

        return True, {
            "current_path": str(path_obj),
            "items": items[:50] # Limit to 50 items to prevent Telegram message overflow
        }, "Thành công"

    except Exception as e:
        logger.error(f"Error listing directory {target_path}: {e}")
        return False, {}, f"Lỗi đọc thư mục: {e}"

def get_file_type_category(filename: str, is_dir: bool) -> str:
    """Return categorical string for UI icon display."""
    if is_dir:
        return "folder"
    ext = Path(filename).suffix.lower()
    if ext in [".txt", ".log", ".md", ".json", ".yaml", ".yml", ".xml", ".csv", ".ini", ".conf", ".cfg"]:
        return "text"
    if ext in [".py", ".js", ".html", ".css", ".sh", ".bat", ".ps1", ".cpp", ".c", ".h", ".rs", ".go", ".java"]:
        return "code"
    if ext in [".zip", ".rar", ".7z", ".tar", ".gz", ".iso"]:
        return "archive"
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".bmp"]:
        return "image"
    if ext in [".mp4", ".mkv", ".avi", ".mov", ".mp3", ".wav"]:
        return "media"
    if ext in [".exe", ".msi", ".dll", ".bin"]:
        return "binary"
    return "file"

def list_directory_web(target_path: Optional[str] = None) -> tuple[bool, Dict[str, Any], str]:
    """
    List contents optimized for Web File Explorer:
    Breadcrumbs, available drives, categorized icons, file size, timestamps.
    """
    try:
        if not target_path or target_path.strip() == "":
            path_obj = Path.cwd()
        else:
            path_obj = Path(target_path).resolve()

        if not path_obj.exists():
            return False, {}, f"Đường dẫn không tồn tại: {target_path}"

        if not path_obj.is_dir():
            return False, {}, f"{target_path} là tệp tin, không phải thư mục."

        # Breadcrumbs
        breadcrumbs = []
        parts = list(path_obj.parts)
        curr = Path(parts[0])
        breadcrumbs.append({"name": parts[0], "path": str(curr)})
        for part in parts[1:]:
            curr = curr / part
            breadcrumbs.append({"name": part, "path": str(curr)})

        items = []
        for entry in sorted(path_obj.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            try:
                stat = entry.stat()
                mtime_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                is_dir = entry.is_dir()
                category = get_file_type_category(entry.name, is_dir)
                items.append({
                    "name": entry.name,
                    "path": str(entry),
                    "is_dir": is_dir,
                    "category": category,
                    "size_bytes": stat.st_size if not is_dir else 0,
                    "size_formatted": format_file_size(stat.st_size) if not is_dir else "-",
                    "mtime": mtime_str,
                    "ext": entry.suffix.lower() if not is_dir else ""
                })
            except (PermissionError, FileNotFoundError):
                items.append({
                    "name": entry.name,
                    "path": str(entry),
                    "is_dir": entry.is_dir(),
                    "category": "locked",
                    "size_bytes": 0,
                    "size_formatted": "Locked",
                    "mtime": "-",
                    "ext": ""
                })

        parent_path = str(path_obj.parent) if path_obj.parent != path_obj else None

        return True, {
            "current_path": str(path_obj),
            "parent_path": parent_path,
            "breadcrumbs": breadcrumbs,
            "drives": get_drives_or_roots(),
            "items": items,
            "total_items": len(items)
        }, "Thành công"
    except Exception as e:
        logger.error(f"Error listing directory web {target_path}: {e}")
        return False, {}, str(e)


def read_text_file(target_path: str, max_lines: int = 60) -> tuple[bool, str]:
    """Read the last N lines or first N lines of a text file."""
    try:
        path = Path(target_path).resolve()
        if not path.exists() or not path.is_file():
            return False, f"Tệp tin không tồn tại: `{target_path}`"

        # Check size: avoid reading huge binary files
        if path.stat().st_size > 5 * 1024 * 1024:
            return False, "Tệp tin quá lớn (> 5MB). Vui lòng dùng lệnh `/download` để tải về."

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        if len(lines) > max_lines:
            content = "".join(lines[-max_lines:])
            return True, f"*(Hiển thị {max_lines} dòng cuối cùng)*:\n```text\n{content}\n```"
        else:
            content = "".join(lines)
            return True, f"```text\n{content}\n```"

    except Exception as e:
        return False, f"Lỗi đọc tệp: {e}"

def save_uploaded_file(data: bytes, target_dir: str, filename: str) -> tuple[bool, str]:
    """Save raw bytes to a target folder on the server."""
    try:
        dir_path = Path(target_dir).resolve()
        dir_path.mkdir(parents=True, exist_ok=True)
        dest_file = dir_path / filename
        with open(dest_file, "wb") as f:
            f.write(data)
        return True, f"Đã lưu tệp thành công tại:\n`{dest_file}` ({format_file_size(len(data))})"
    except Exception as e:
        logger.error(f"Error saving file {filename}: {e}")
        return False, f"Lỗi khi lưu tệp: {e}"

def delete_path(target_path: str) -> tuple[bool, str]:
    """Delete a file or folder permanently."""
    try:
        path = Path(target_path).resolve()
        if not path.exists():
            return False, f"Đường dẫn không tồn tại: `{target_path}`"

        if path.is_dir():
            shutil.rmtree(path)
            return True, f"🗑️ Đã xóa thư mục: `{path}`"
        else:
            path.unlink()
            return True, f"🗑️ Đã xóa tệp: `{path}`"
    except Exception as e:
        return False, f"Lỗi xóa: {e}"

def make_directory(target_path: str) -> tuple[bool, str]:
    """Create a new folder."""
    try:
        path = Path(target_path).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return True, f"📁 Đã tạo thư mục thành công:\n`{path}`"
    except Exception as e:
        return False, f"Lỗi tạo thư mục: {e}"
