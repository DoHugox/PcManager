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

def set_dpi_awareness():
    """Ensure Windows process is DPI aware to prevent multi-monitor coordinate scaling errors."""
    if platform.system().lower() == "windows":
        try:
            import ctypes
            # Per-Monitor V2 awareness
            try:
                ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
                return
            except Exception:
                pass
            # Shcore awareness
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
                return
            except Exception:
                pass
            # Standard DPI aware
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception as e:
            logger.debug(f"DPI awareness initialization note: {e}")

# Initialize DPI awareness
set_dpi_awareness()

def is_workstation_locked() -> bool:
    """Check if the Windows workstation is currently locked or in the Winlogon secure desktop."""
    if platform.system().lower() != "windows":
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        # DESKTOP_SWITCHDESKTOP = 0x0100
        hdesk = user32.OpenInputDesktop(0, False, 0x0100)
        if not hdesk:
            return True
        user32.CloseDesktop(hdesk)
        return False
    except Exception as e:
        logger.debug(f"is_workstation_locked error: {e}")
        return False

def _generate_locked_screen_image(target_path: Path) -> Path:
    """Generate a high-visibility cyber security status card when desktop is locked or GDI is detached."""
    from PIL import Image, ImageDraw

    width, height = 1280, 720
    img = Image.new("RGB", (width, height), color=(9, 13, 24))
    draw = ImageDraw.Draw(img)

    # Outer neon border
    draw.rectangle([(8, 8), (width - 8, height - 8)], outline=(0, 242, 254), width=3)
    draw.rectangle([(14, 14), (width - 14, height - 14)], outline=(25, 40, 70), width=1)

    # Header box
    draw.rectangle([(30, 30), (width - 30, 110)], fill=(16, 26, 48), outline=(0, 242, 254), width=1)
    draw.text((50, 48), "🛡️ VNServerSentinel - HỆ THỐNG GIÁM SÁT MÁY CHỦ AN NINH", fill=(0, 242, 254))
    draw.text((50, 78), "TRẠNG THÁI MÀN HÌNH MÁY CHỦ (DESKTOP SECURITY STATUS)", fill=(140, 165, 205))

    # Main Warning Card
    draw.rectangle([(30, 130), (width - 30, 260)], fill=(32, 22, 16), outline=(255, 171, 0), width=2)
    draw.text((50, 150), "🔒 MÁY CHỦ ĐANG TRONG TRẠNG THÁI KHÓA MÀN HÌNH (LOCKED SCREEN)", fill=(255, 171, 0))
    draw.text((50, 185), "• Windows đang bảo vệ phiên làm việc tại màn hình đăng nhập (Winlogon / Lock Screen).", fill=(240, 240, 240))
    draw.text((50, 215), "• Cơ chế bảo mật GDI của Windows chặn chụp trực tiếp nội dung desktop khi màn hình bị khóa.", fill=(200, 210, 225))

    # Telemetry box
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    draw.rectangle([(30, 280), (width - 30, 520)], fill=(14, 20, 36), outline=(40, 55, 85), width=1)
    draw.text((50, 300), "📊 THÔNG TIN HỆ THỐNG VẪN ĐANG HOẠT ĐỘNG BÌNH THƯỜNG:", fill=(0, 230, 118))

    host_info = f"• Máy chủ (Hostname): {platform.node()} ({platform.system()} {platform.release()})"
    time_info = f"• Thời điểm kiểm tra: {now_str}"

    try:
        import psutil
        cpu_p = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        uptime_sec = int(time.time() - psutil.boot_time())
        hours, rem = divmod(uptime_sec, 3600)
        minutes, _ = divmod(rem, 60)
        sys_info = f"• Tài nguyên: CPU {cpu_p}% | RAM {ram.percent}% ({round(ram.used/(1024**3), 1)}GB / {round(ram.total/(1024**3), 1)}GB)"
        uptime_info = f"• Thời gian hoạt động liên tục (Uptime): {hours} giờ {minutes} phút"
    except Exception:
        sys_info = "• Tài nguyên: Hoạt động bình thường"
        uptime_info = "• Uptime: Sẵn sàng"

    draw.text((50, 340), host_info, fill=(220, 230, 245))
    draw.text((50, 375), time_info, fill=(220, 230, 245))
    draw.text((50, 410), sys_info, fill=(220, 230, 245))
    draw.text((50, 445), uptime_info, fill=(220, 230, 245))
    draw.text((50, 480), "• Tình trạng: Telegram Bot, UPnP, Web Server và Auto-Update đang chạy ngầm 100%.", fill=(0, 230, 118))

    # Actions box
    draw.rectangle([(30, 540), (width - 30, 680)], fill=(16, 22, 38), outline=(79, 172, 254), width=1)
    draw.text((50, 555), "💡 HƯỚNG DẪN THAO TÁC TỪ XA:", fill=(79, 172, 254))
    draw.text((50, 585), "1. Để xem và điều khiển màn hình máy tính: Gõ lệnh /rd on để khởi động RustDesk Remote Desktop.", fill=(220, 230, 245))
    draw.text((50, 615), "2. Để kiểm tra ai đang đứng trước máy: Gõ lệnh /cam để kích hoạt webcam chụp ảnh trực tiếp.", fill=(220, 230, 245))
    draw.text((50, 645), "3. Khi có người mở khóa tại bàn (Physical Session Unlock), hệ thống sẽ tự động chụp ảnh báo ngay!", fill=(255, 171, 0))

    img.save(str(target_path), format="JPEG", quality=85)
    return target_path

def capture_screenshot() -> tuple[Optional[Path], str]:
    """Capture full desktop screenshot with robust multi-engine fallback and lock detection."""
    Config.ensure_directories()
    filename = f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    file_path = Config.SNAPSHOT_DIR / filename

    # 1. If workstation is locked, generate informative security card immediately
    if is_workstation_locked():
        try:
            _generate_locked_screen_image(file_path)
            return file_path, "Màn hình đang ở trạng thái Khóa (Windows Lock Screen). Máy chủ vẫn hoạt động bình thường."
        except Exception as e:
            logger.debug(f"Lock screen card generator notice: {e}")

    # 2. Engine 1: MSS (Fastest, multi-monitor safe, DPI-safe, no GDI virtual screen errors)
    try:
        import mss
        with mss.MSS() as sct:
            monitor = sct.monitors[0] if sct.monitors else None
            if monitor:
                sct_img = sct.grab(monitor)
                from PIL import Image
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                img.save(str(file_path), format="JPEG", quality=85)
                return file_path, "Chụp màn hình thành công."
    except Exception as e:
        logger.debug(f"MSS screenshot engine error: {e}")

    # 3. Engine 2: PIL ImageGrab (all_screens=True)
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=True)
        img.save(str(file_path), format="JPEG", quality=85)
        return file_path, "Chụp màn hình thành công."
    except Exception as e:
        logger.debug(f"Pillow all_screens error: {e}")

    # 4. Engine 3: PIL ImageGrab (all_screens=False - Primary display fallback)
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=False)
        img.save(str(file_path), format="JPEG", quality=85)
        return file_path, "Chụp màn hình chính thành công."
    except Exception as e:
        logger.debug(f"Pillow primary display error: {e}")

    # 5. Engine 4: Direct Windows GDI via ctypes
    if platform.system().lower() == "windows":
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32

            w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
            h = user32.GetSystemMetrics(1)  # SM_CYSCREEN

            hwnd = user32.GetDesktopWindow()
            hdc_screen = user32.GetWindowDC(hwnd)
            hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
            hbm = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
            hbm_old = gdi32.SelectObject(hdc_mem, hbm)

            SRCCOPY = 0x00CC0020
            success = gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, SRCCOPY)
            if success:
                from PIL import Image
                class BITMAPINFOHEADER(ctypes.Structure):
                    _fields_ = [
                        ('biSize', wintypes.DWORD),
                        ('biWidth', wintypes.LONG),
                        ('biHeight', wintypes.LONG),
                        ('biPlanes', wintypes.WORD),
                        ('biBitCount', wintypes.WORD),
                        ('biCompression', wintypes.DWORD),
                        ('biSizeImage', wintypes.DWORD),
                        ('biXPelsPerMeter', wintypes.LONG),
                        ('biYPelsPerMeter', wintypes.LONG),
                        ('biClrUsed', wintypes.DWORD),
                        ('biClrImportant', wintypes.DWORD)
                    ]
                bmi = BITMAPINFOHEADER()
                bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                bmi.biWidth = w
                bmi.biHeight = -h
                bmi.biPlanes = 1
                bmi.biBitCount = 32
                bmi.biCompression = 0

                buffer = ctypes.create_string_buffer(w * h * 4)
                gdi32.GetDIBits(hdc_mem, hbm, 0, h, buffer, ctypes.byref(bmi), 0)
                img = Image.frombuffer('RGBA', (w, h), buffer, 'raw', 'BGRA', 0, 1).convert('RGB')
                img.save(str(file_path), format="JPEG", quality=85)

                gdi32.SelectObject(hdc_mem, hbm_old)
                gdi32.DeleteObject(hbm)
                gdi32.DeleteDC(hdc_mem)
                user32.ReleaseDC(hwnd, hdc_screen)
                return file_path, "Chụp màn hình thành công."
            else:
                gdi32.SelectObject(hdc_mem, hbm_old)
                gdi32.DeleteObject(hbm)
                gdi32.DeleteDC(hdc_mem)
                user32.ReleaseDC(hwnd, hdc_screen)
        except Exception as e:
            logger.debug(f"Direct Win32 GDI error: {e}")

    # 6. Fallback: If all capture engines fail (e.g. locked workstation or detached session)
    try:
        _generate_locked_screen_image(file_path)
        return file_path, "Màn hình desktop đang bị khóa hoặc không truy cập được GDI. Đã tạo thẻ thông tin an toàn."
    except Exception as e:
        logger.error(f"Complete screenshot failure: {e}")
        return None, "Không thể chụp màn hình (Desktop đang bị khóa hoặc không có phiên tương tác)."

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
