"""
VNServerSentinel - On-Demand Remote Desktop Controller (RustDesk / AnyDesk)
Optimized for Core i3 5th Gen (saves 150-300MB RAM by only running when requested).
"""

import os
import sys
import time
import shutil
import logging
import subprocess
import urllib.request
from pathlib import Path
from typing import Tuple, Optional

from config import Config

logger = logging.getLogger("VNServerSentinel.RemoteDesktop")

TOOLS_DIR = Config.DATA_DIR / "tools"
RUSTDESK_PATH = TOOLS_DIR / "rustdesk.exe"
RUSTDESK_OFFICIAL_URL = "https://github.com/rustdesk/rustdesk/releases/download/1.2.3/rustdesk-1.2.3-x86_64.exe"

def is_process_running(process_name: str) -> bool:
    """Check if a process is currently active."""
    try:
        if os.name == "nt":
            out = subprocess.check_output(f'tasklist /fi "imagename eq {process_name}"', shell=True, text=True)
            return process_name.lower() in out.lower()
        else:
            out = subprocess.check_output(f'pgrep -f {process_name}', shell=True, text=True)
            return bool(out.strip())
    except Exception:
        return False

def get_installed_rustdesk() -> Optional[Path]:
    """Find RustDesk executable either in local tools or Program Files."""
    if RUSTDESK_PATH.exists():
        return RUSTDESK_PATH

    installed_candidates = [
        Path("C:/Program Files/RustDesk/rustdesk.exe"),
        Path("C:/Program Files (x86)/RustDesk/rustdesk.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "RustDesk" / "rustdesk.exe"
    ]
    for p in installed_candidates:
        if p.exists():
            return p
    return None

def start_remote_desktop() -> tuple[bool, str]:
    """
    Launch RustDesk on-demand. If not present, downloads portable version automatically.
    """
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    exe_path = get_installed_rustdesk()

    if not exe_path:
        # Download lightweight portable RustDesk
        logger.info("RustDesk not found. Downloading portable version...")
        try:
            req = urllib.request.Request(
                RUSTDESK_OFFICIAL_URL,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp, open(RUSTDESK_PATH, "wb") as f:
                shutil.copyfileobj(resp, f)
            exe_path = RUSTDESK_PATH
            logger.info("Downloaded portable RustDesk successfully.")
        except Exception as e:
            logger.error(f"Download RustDesk failed: {e}")
            # Fallback: check if AnyDesk is available
            if Path("C:/Program Files (x86)/AnyDesk/AnyDesk.exe").exists():
                subprocess.Popen(["C:/Program Files (x86)/AnyDesk/AnyDesk.exe"])
                return True, "🟢 Đã kích hoạt AnyDesk có sẵn trên máy!"
            return False, f"Chưa có RustDesk và tải tự động thất bại: {e}. Bạn có thể copy rustdesk.exe vào `data/tools/`."

    if is_process_running(exe_path.name):
        return True, f"🟢 RustDesk hiện ĐANG CHẠY trên máy chủ!\n(Dùng lệnh `/rd off` để tắt khi xong)."

    try:
        # Start RustDesk detached in user session
        if os.name == "nt":
            subprocess.Popen([str(exe_path)], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            subprocess.Popen([str(exe_path)])

        time.sleep(2)
        return True, (
            "🚀 *RUSTDESK ĐÃ ĐƯỢC BẬT THÀNH CÔNG!*\n\n"
            "🖥️ Phần mềm điều khiển đồ họa đang chạy ngầm.\n"
            "👉 Hãy mở RustDesk trên máy tính/điện thoại tại Đài Loan và nhập ID để kết nối.\n\n"
            "⚠️ *Lưu ý:* Khi điều khiển xong, hãy gõ `/rd off` để tắt hẳn, giải phóng 200MB RAM cho chiếc Core i3!"
        )
    except Exception as e:
        logger.error(f"Error starting RustDesk: {e}")
        return False, f"Lỗi khởi chạy RustDesk: {e}"

def stop_remote_desktop() -> tuple[bool, str]:
    """Terminate RustDesk to reclaim RAM & CPU."""
    stopped = False
    for proc in ("rustdesk.exe", "AnyDesk.exe"):
        if is_process_running(proc):
            try:
                subprocess.run(f"taskkill /f /im {proc}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                stopped = True
            except Exception:
                pass

    if stopped:
        return True, "🛑 *ĐÃ TẮT REMOTE DESKTOP HOÀN TOÀN!*\n✅ Đã giải phóng ~200MB RAM và tài nguyên CPU cho máy chủ."
    return True, "ℹ️ Remote Desktop (RustDesk/AnyDesk) hiện không chạy."

def get_remote_desktop_status() -> str:
    """Return current status of Remote Desktop."""
    rd_running = is_process_running("rustdesk.exe")
    any_running = is_process_running("AnyDesk.exe")
    if rd_running:
        return "🟢 RustDesk: Đang chạy (Active)"
    if any_running:
        return "🟢 AnyDesk: Đang chạy (Active)"
    return "⚪ Remote Desktop: Đang tắt (Tiết kiệm RAM)"
