"""
VNServerSentinel - Physical Security & Intruder Guard
Detects physical session unlocks, captures webcam and desktop screenshots,
and enables remote workstation locking.
"""

import os
import sys
import time
import logging
import platform
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from config import Config

logger = logging.getLogger("VNServerSentinel.Security")

def capture_webcam() -> tuple[Optional[Path], str]:
    """Capture photo from webcam if available."""
    if not Config.ENABLE_WEBCAM:
        return None, "Webcam đã bị tắt trong cấu hình."

    try:
        import cv2
        # Try primary camera (0), then secondary (1)
        for cam_id in (0, 1):
            cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW if platform.system().lower() == "windows" else cv2.CAP_ANY)
            if cap.isOpened():
                # Allow camera sensor to auto-expose
                for _ in range(5):
                    ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    Config.ensure_directories()
                    filename = f"webcam_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    file_path = Config.SNAPSHOT_DIR / filename
                    cv2.imwrite(str(file_path), frame)
                    return file_path, "Chụp webcam thành công."
        return None, "Không tìm thấy webcam khả dụng trên máy chủ."
    except ImportError:
        return None, "Thư viện opencv-python chưa được cài đặt."
    except Exception as e:
        logger.error(f"Webcam capture error: {e}")
        return None, f"Lỗi khi chụp webcam: {e}"

def capture_screenshot() -> tuple[Optional[Path], str]:
    """Capture full desktop screenshot (including multiple monitors)."""
    try:
        from PIL import ImageGrab
        Config.ensure_directories()
        filename = f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        file_path = Config.SNAPSHOT_DIR / filename
        
        # Capture all monitors
        img = ImageGrab.grab(all_screens=True)
        img.save(str(file_path), format="JPEG", quality=85)
        return file_path, "Chụp màn hình thành công."
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return None, f"Lỗi khi chụp màn hình: {e}"

def lock_workstation() -> tuple[bool, str]:
    """Lock the Windows workstation immediately."""
    if platform.system().lower() == "windows":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            res = user32.LockWorkStation()
            if res:
                return True, "🔒 Đã khóa màn hình máy tính Windows thành công!"
            return False, "Không thể khóa máy (mã lỗi từ user32)."
        except Exception as e:
            return False, f"Lỗi khi gọi LockWorkStation: {e}"
    else:
        logger.info("[Mock Lock] LockWorkStation called on non-Windows.")
        return True, "[Mock] Đã gửi lệnh khóa màn hình."

class SessionWatcher(threading.Thread):
    """
    Background worker that listens for Windows Session Unlock events.
    Differentiates between Physical Console unlock and Remote Desktop.
    """
    def __init__(self, on_intruder_callback: Callable[[dict], None]):
        super().__init__(daemon=True)
        self.on_intruder_callback = on_intruder_callback
        self.running = True

    def run(self):
        if platform.system().lower() != "windows":
            logger.info("Non-Windows OS: Windows Session Watcher skipped.")
            return

        try:
            import ctypes
            from ctypes import wintypes

            WM_WTSSESSION_CHANGE = 0x02B1
            WTS_CONSOLE_CONNECT = 0x1
            WTS_CONSOLE_DISCONNECT = 0x2
            WTS_REMOTE_CONNECT = 0x3
            WTS_REMOTE_DISCONNECT = 0x4
            WTS_SESSION_LOGON = 0x5
            WTS_SESSION_LOGOFF = 0x6
            WTS_SESSION_LOCK = 0x7
            WTS_SESSION_UNLOCK = 0x8
            NOTIFY_FOR_ALL_SESSIONS = 1

            wtsapi32 = ctypes.windll.wtsapi32
            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32

            WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

            def wnd_proc(hwnd, msg, wparam, lparam):
                if msg == WM_WTSSESSION_CHANGE:
                    event_code = wparam
                    session_id = lparam
                    console_session_id = kernel32.WTSGetActiveConsoleSessionId()
                    is_physical = (session_id == console_session_id)

                    logger.info(f"Session Event: code={event_code}, session={session_id}, console={console_session_id}, is_physical={is_physical}")

                    if event_code == WTS_SESSION_UNLOCK and is_physical:
                        logger.warning("🚨 PHÁT HIỆN MỞ KHÓA MÁY TRỰC TIẾP TẠI BÀN (Physical Unlock)!")
                        self._handle_intruder_event(session_id, "Physical Unlock (Mở khóa tại chỗ)")
                    elif event_code == WTS_CONSOLE_CONNECT:
                        logger.warning("🚨 PHÁT HIỆN KẾT NỐI MÀN HÌNH VẬT LÝ (Console Connect)!")
                        self._handle_intruder_event(session_id, "Console Connect (Cắm/Mở màn hình trực tiếp)")
                    elif event_code == WTS_SESSION_LOGON and is_physical:
                        logger.warning("🚨 PHÁT HIỆN ĐĂNG NHẬP TRỰC TIẾP (Console Logon)!")
                        self._handle_intruder_event(session_id, "Console Logon (Đăng nhập tại chỗ)")

                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

            # Register Windows Window Class
            wc = wintypes.WNDCLASS()
            wc.lpfnWndProc = WNDPROC(wnd_proc)
            wc.lpszClassName = "VNServerSentinel_SessionWatcher"
            wc.hInstance = kernel32.GetModuleHandleW(None)
            atom = user32.RegisterClassW(ctypes.byref(wc))

            if not atom:
                logger.error("Failed to register window class for session watcher.")
                return

            hwnd = user32.CreateWindowExW(
                0, wc.lpszClassName, "SessionWatcherWin", 0, 0, 0, 0, 0,
                0, 0, wc.hInstance, None
            )

            if not hwnd:
                logger.error("Failed to create message window for session watcher.")
                return

            # Register for session notifications
            wtsapi32.WTSRegisterSessionNotification(hwnd, NOTIFY_FOR_ALL_SESSIONS)
            logger.info("Windows Session Watcher registered successfully.")

            # Windows Message Pump
            msg = wintypes.MSG()
            while self.running:
                b_ret = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
                if b_ret != 0:
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))

        except Exception as e:
            logger.error(f"Error in Windows Session Watcher loop: {e}")

    def _handle_intruder_event(self, session_id: int, event_desc: str):
        """Take snapshots and alert owner."""
        cam_path, _ = capture_webcam()
        screen_path, _ = capture_screenshot()
        event_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event": event_desc,
            "session_id": session_id,
            "webcam_image": cam_path,
            "screen_image": screen_path
        }
        if self.on_intruder_callback:
            try:
                self.on_intruder_callback(event_data)
            except Exception as e:
                logger.error(f"Error calling on_intruder_callback: {e}")
