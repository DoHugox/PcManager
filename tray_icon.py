"""
VNServerSentinel - Windows System Tray Icon & Quick Context Menu
Provides a persistent icon in the system notification area (near the clock)
with quick actions: Open Dashboard, Screen, Cam, Lock, RustDesk, Exit.
"""

import sys
import logging
import threading
import webbrowser
from pathlib import Path
from typing import Callable, Optional

from PIL import Image

from config import Config
import security_guard
import remote_desktop

logger = logging.getLogger("VNServerSentinel.Tray")

class SystemTrayManager:
    def __init__(self, on_exit_callback: Optional[Callable] = None):
        self.on_exit_callback = on_exit_callback
        self.icon = None
        self._thread = None

    def start(self):
        """Start the system tray icon in a dedicated thread."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _get_icon_image(self) -> Image.Image:
        icon_path = Config.BASE_DIR / "assets" / "app.png"
        if not icon_path.exists():
            icon_path = Config.BASE_DIR / "assets" / "app.ico"
        if icon_path.exists():
            try:
                return Image.open(icon_path)
            except Exception as e:
                logger.warning(f"Failed to load icon image: {e}")
        # Generate a fallback 64x64 cyan shield icon in memory
        img = Image.new("RGBA", (64, 64), color=(0, 242, 254, 255))
        return img

    def _open_dashboard(self, icon=None, item=None):
        webbrowser.open("http://localhost:8888")

    def _action_screen(self, icon=None, item=None):
        security_guard.capture_screenshot()

    def _action_cam(self, icon=None, item=None):
        security_guard.capture_webcam()

    def _action_lock(self, icon=None, item=None):
        security_guard.lock_workstation()

    def _toggle_rd(self, icon=None, item=None):
        rd_status = remote_desktop.get_remote_desktop_status()
        if "đang hoạt động" in rd_status:
            remote_desktop.stop_remote_desktop()
        else:
            remote_desktop.start_remote_desktop()

    def _exit_app(self, icon=None, item=None):
        logger.info("Exiting application completely from system tray...")
        try:
            if self.icon:
                self.icon.stop()
        except Exception:
            pass

        if self.on_exit_callback:
            try:
                self.on_exit_callback()
            except Exception:
                pass

        import os
        import subprocess
        if sys.platform == "win32":
            try:
                subprocess.Popen("taskkill /F /T /IM PcManager.exe", shell=True)
            except Exception:
                pass
        os._exit(0)

    def _run(self):
        try:
            import pystray
            from pystray import MenuItem as item

            image = self._get_icon_image()
            menu = pystray.Menu(
                item("🌐 Mở Web Dashboard (http://localhost:8888)", self._open_dashboard, default=True),
                pystray.Menu.SEPARATOR,
                item("📸 Chụp Màn Hình Ngay", self._action_screen),
                item("📷 Chụp Webcam Kẻ Ngồi Máy", self._action_cam),
                item("🔒 Khóa Màn Hình Lập Tức", self._action_lock),
                item("🖥️ Bật/Tắt RustDesk Remote Desktop", self._toggle_rd),
                pystray.Menu.SEPARATOR,
                item("❌ Thoát PcManager Hoàn Toàn", self._exit_app)
            )

            self.icon = pystray.Icon(
                "PcManager",
                image,
                "PcManager - Quản Trị Máy Chủ Từ Xa (Đang Chạy)",
                menu
            )
            logger.info("System Tray Icon started successfully.")
            self.icon.run()
        except ImportError:
            logger.warning("pystray library not available. System tray icon disabled.")
        except Exception as e:
            logger.error(f"Error running system tray icon: {e}")
