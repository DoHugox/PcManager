"""
VNServerSentinel - Native Desktop Management Application
Provides a native, modern desktop application window (via pywebview & Edge WebView2)
replacing external web browsers with a dedicated GUI client.
"""

import sys
import logging
import threading
from pathlib import Path
from typing import Optional, Callable

from config import Config

logger = logging.getLogger("VNServerSentinel.DesktopUI")

class DesktopUIManager:
    _instance: Optional["DesktopUIManager"] = None

    def __init__(self):
        self.window = None
        self.port: int = 8888
        self.on_exit_callback: Optional[Callable] = None
        self.is_native_active: bool = False
        self._closing_to_tray: bool = True

    @classmethod
    def get_instance(cls) -> "DesktopUIManager":
        if cls._instance is None:
            cls._instance = DesktopUIManager()
        return cls._instance

    def show_window(self) -> bool:
        """Bring native desktop window to foreground, restore and unhide."""
        if self.window:
            try:
                self.window.show()
                self.window.restore()
                return True
            except Exception as e:
                logger.debug(f"Could not restore native window: {e}")

        # If window is not running or failed, open in browser as fallback
        try:
            import webbrowser
            webbrowser.open(f"http://localhost:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to open browser fallback: {e}")
            return False

    def hide_window(self):
        """Minimize/hide window to system tray."""
        if self.window:
            try:
                self.window.hide()
            except Exception as e:
                logger.debug(f"Error hiding window: {e}")

    def exit_completely(self):
        """Cleanly destroy window and trigger app shutdown."""
        self._closing_to_tray = False
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
        if self.on_exit_callback:
            try:
                self.on_exit_callback()
            except Exception:
                pass

    def launch(self, port: int = 8888, on_exit: Optional[Callable] = None) -> bool:
        """
        Launch the Native Desktop Application Window.
        Uses Microsoft Edge WebView2 on Windows for zero-overhead, high-performance rendering.
        Falls back smoothly to standard web browser if running in headless or unsupported mode.
        """
        self.port = port
        self.on_exit_callback = on_exit

        # Check for silent / service / background flags
        if any(arg in sys.argv for arg in ("--service", "--silent", "--minimized", "--no-gui")):
            logger.info("Running in silent/service mode. Desktop UI window suppressed.")
            return False

        try:
            import webview

            # Locate application icon
            icon_path = Config.BASE_DIR / "assets" / "app.ico"
            if not icon_path.exists():
                icon_path = Config.BASE_DIR / "assets" / "app.png"

            # Create native application window
            self.window = webview.create_window(
                title="PcManager - Trung Tâm Quản Trị Máy Chủ Từ Xa",
                url=f"http://127.0.0.1:{self.port}",
                width=1280,
                height=820,
                min_size=(960, 600),
                text_select=True,
                zoomable=True,
                confirm_close=False
            )

            # Window event: Intercept close [X] button
            def on_closing():
                if self._closing_to_tray:
                    logger.info("Window close clicked: Minimizing to Windows System Tray.")
                    try:
                        self.window.hide()
                    except Exception:
                        pass
                    return False  # Prevent window destruction, keeps background services alive
                return True

            self.window.events.closing += on_closing
            self.is_native_active = True
            logger.info("Native Desktop UI (PyWebView / WebView2) initialized successfully.")

            # webview.start blocks until window is closed or app exits
            webview.start(debug=False)
            return True

        except Exception as e:
            logger.warning(f"Native Desktop UI could not start ({e}). Falling back to browser.")
            self.is_native_active = False
            try:
                import webbrowser
                webbrowser.open(f"http://localhost:{self.port}")
            except Exception:
                pass
            return False
