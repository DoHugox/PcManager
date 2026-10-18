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

# Awake Mode State
_awake_active: bool = False
_awake_thread: Optional[threading.Thread] = None

def _wake_display_if_possible():
    """Wake monitor display from DPMS standby or screen saver."""
    if platform.system().lower() == "windows":
        try:
            import ctypes
            # ES_SYSTEM_REQUIRED = 0x00000001, ES_DISPLAY_REQUIRED = 0x00000002
            ctypes.windll.kernel32.SetThreadExecutionState(0x00000001 | 0x00000002)
            # Gentle mouse move delta 0,0 to prompt display wake
            ctypes.windll.user32.mouse_event(0x0001, 0, 0, 0, 0)
        except Exception:
            pass

def _awake_pulse_loop():
    """Periodically pulse Windows execution state every 30s while awake mode is active."""
    while _awake_active:
        _wake_display_if_possible()
        time.sleep(30)

def set_awake_mode(enable: bool) -> tuple[bool, str]:
    """
    Enable or disable Awake mode (Keep display on, prevent Windows sleep/auto-lock).
    Uses SetThreadExecutionState on Windows.
    """
    global _awake_active, _awake_thread
    _awake_active = enable
    if platform.system().lower() == "windows":
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_DISPLAY_REQUIRED = 0x00000002
            if enable:
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
                )
                if not _awake_thread or not _awake_thread.is_alive():
                    _awake_thread = threading.Thread(target=_awake_pulse_loop, daemon=True)
                    _awake_thread.start()
                return True, "☕ Đã KÍCH HOẠT chế độ Giữ Màn Hình Sáng (Awake Mode). Máy sẽ không tắt màn hình hay sleep!"
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                return True, "💤 Đã TẮT chế độ Giữ Màn Hình Sáng. Windows sẽ áp dụng quy tắc tiết kiệm điện bình thường."
        except Exception as e:
            logger.error(f"Error setting awake state: {e}")
            return False, f"Lỗi khi cài đặt Awake: {e}"
    else:
        return True, f"[Mock] Awake mode set to {enable}."

def get_awake_mode() -> bool:
    """Return whether awake mode is currently active."""
    return _awake_active

def wake_display() -> bool:
    """Send immediate wake signal to monitor."""
    _wake_display_if_possible()
    return True

def is_workstation_locked() -> bool:
    """Check if the Windows workstation is currently locked or in the Winlogon secure desktop."""
    if platform.system().lower() != "windows":
        return False
    try:
        import ctypes
        from ctypes.wintypes import BOOL, DWORD, HANDLE, LPCWSTR
        user32 = ctypes.WinDLL('user32', use_last_error=True)

        # Check OpenInputDesktop
        # DESKTOP_SWITCHDESKTOP = 0x0100
        hdesk = user32.OpenInputDesktop(0, False, 0x0100)
        if not hdesk:
            return True
        user32.CloseDesktop(hdesk)

        # Check SwitchDesktop on default desktop
        open_desktop = user32.OpenDesktopW
        switch_desktop = user32.SwitchDesktop
        close_desktop = user32.CloseDesktop
        open_desktop.argtypes = (LPCWSTR, DWORD, BOOL, DWORD)
        open_desktop.restype = HANDLE
        switch_desktop.argtypes = (HANDLE,)
        switch_desktop.restype = DWORD
        close_desktop.argtypes = (HANDLE,)
        close_desktop.restype = DWORD

        hnd = open_desktop('default', 0, False, 0x0100)
        if hnd:
            res = switch_desktop(hnd)
            close_desktop(hnd)
            if not bool(res):
                return True
        return False
    except Exception as e:
        logger.debug(f"is_workstation_locked error: {e}")
        return False

def _get_font(size: int = 16):
    """Safely return a Unicode-compatible font with multi-OS and Pillow fallback."""
    from PIL import ImageFont
    candidates = [
        "segoeui.ttf", "arial.ttf", "tahoma.ttf", "calibri.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()

def _safe_draw_text(draw, pos, text, fill, font=None):
    """Safely draw text; falls back to normalized ASCII if font cannot encode non-Latin characters."""
    import unicodedata
    try:
        draw.text(pos, text, fill=fill, font=font)
    except Exception:
        try:
            safe_ascii = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
            draw.text(pos, safe_ascii, fill=fill, font=font)
        except Exception:
            try:
                draw.text(pos, text, fill=fill)
            except Exception:
                pass

def _generate_locked_screen_image(target_path: Path) -> Path:
    """Generate a high-visibility cyber security status card when desktop is locked or GDI is detached."""
    from PIL import Image, ImageDraw
    Config.ensure_directories()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        width, height = 1280, 720
        img = Image.new("RGB", (width, height), color=(9, 13, 24))
        draw = ImageDraw.Draw(img)

        f_title = _get_font(22)
        f_header = _get_font(17)
        f_body = _get_font(15)
        f_small = _get_font(13)

        # Outer neon border
        draw.rectangle([(8, 8), (width - 8, height - 8)], outline=(0, 242, 254), width=3)
        draw.rectangle([(14, 14), (width - 14, height - 14)], outline=(25, 40, 70), width=1)

        # Header box
        draw.rectangle([(30, 25), (width - 30, 95)], fill=(16, 26, 48), outline=(0, 242, 254), width=1)
        _safe_draw_text(draw, (50, 36), "VNServerSentinel - HỆ THỐNG GIÁM SÁT MÁY CHỦ AN NINH", fill=(0, 242, 254), font=f_title)
        _safe_draw_text(draw, (50, 68), "TRẠNG THÁI MÀN HÌNH MÁY CHỦ (DESKTOP SECURITY STATUS)", fill=(140, 165, 205), font=f_small)

        # Main Warning Card
        draw.rectangle([(30, 110), (width - 30, 230)], fill=(32, 22, 16), outline=(255, 171, 0), width=2)
        _safe_draw_text(draw, (50, 125), "[KHÓA] MÁY CHỦ ĐANG TRONG TRẠNG THÁI KHÓA MÀN HÌNH (LOCKED SCREEN)", fill=(255, 171, 0), font=f_header)
        _safe_draw_text(draw, (50, 160), "• Windows đang bảo vệ phiên làm việc tại màn hình đăng nhập (Winlogon / Secure Desktop).", fill=(240, 240, 240), font=f_body)
        _safe_draw_text(draw, (50, 190), "• Cơ chế bảo mật GDI của Windows chặn chụp trực tiếp nội dung desktop khi màn hình bị khóa.", fill=(200, 210, 225), font=f_body)

        # Telemetry box
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        draw.rectangle([(30, 245), (width - 30, 500)], fill=(14, 20, 36), outline=(40, 55, 85), width=1)
        _safe_draw_text(draw, (50, 260), "THÔNG TIN HỆ THỐNG VẪN ĐANG HOẠT ĐỘNG BÌNH THƯỜNG 100%:", fill=(0, 230, 118), font=f_header)

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

        # Active listening services info (Minecraft, 9router, Web, etc.)
        services_info = "• Dịch vụ & Cổng mạng: Web Dashboard:8888 | Telegram Bot: Online"
        try:
            import system_monitor
            svcs = system_monitor.get_active_listening_services()
            if svcs:
                svc_items = [f"{s.get('name')}:{s.get('port')}" for s in svcs[:4]]
                services_info = "• Dịch vụ đang mở port: " + " | ".join(svc_items)
        except Exception:
            pass

        _safe_draw_text(draw, (50, 295), host_info, fill=(220, 230, 245), font=f_body)
        _safe_draw_text(draw, (50, 325), time_info, fill=(220, 230, 245), font=f_body)
        _safe_draw_text(draw, (50, 355), sys_info, fill=(220, 230, 245), font=f_body)
        _safe_draw_text(draw, (50, 385), uptime_info, fill=(220, 230, 245), font=f_body)
        _safe_draw_text(draw, (50, 415), services_info, fill=(0, 242, 254), font=f_body)
        _safe_draw_text(draw, (50, 445), "• Tình trạng: Telegram Bot, UPnP, Web Server và Auto-Update đang chạy ngầm 100%.", fill=(0, 230, 118), font=f_body)

        # Actions box
        draw.rectangle([(30, 515), (width - 30, 690)], fill=(16, 22, 38), outline=(79, 172, 254), width=1)
        _safe_draw_text(draw, (50, 530), "HƯỚNG DẪN THAO TÁC VÀ ĐIỀU KHIỂN TỪ XA:", fill=(79, 172, 254), font=f_header)
        _safe_draw_text(draw, (50, 565), "1. Xem & điều khiển màn hình máy tính: Gõ lệnh /rd on để khởi động RustDesk Remote Desktop.", fill=(220, 230, 245), font=f_body)
        _safe_draw_text(draw, (50, 595), "2. Kiểm tra ai đang đứng trước máy chủ: Gõ lệnh /cam để kích hoạt webcam chụp ảnh trực tiếp.", fill=(220, 230, 245), font=f_body)
        _safe_draw_text(draw, (50, 625), "3. Giữ màn hình luôn sáng không bị khóa: Gõ lệnh /awake on (ngăn Windows tắt màn hình/sleep).", fill=(220, 230, 245), font=f_body)
        _safe_draw_text(draw, (50, 655), "4. Chạy lệnh CMD từ xa: Gõ /cmd <lệnh> (Ví dụ: /cmd dir hoặc /services).", fill=(255, 171, 0), font=f_body)

        img.save(str(target_path), format="JPEG", quality=85)
        return target_path
    except Exception as e:
        logger.error(f"Error drawing detailed card, generating minimal fallback: {e}")
        try:
            # Bulletproof fallback solid card so file_path ALWAYS exists
            img = Image.new("RGB", (1000, 500), color=(15, 20, 32))
            draw = ImageDraw.Draw(img)
            draw.text((30, 40), "VNServerSentinel - Windows Workstation Locked / Session Isolated", fill=(0, 242, 254))
            draw.text((30, 80), "Desktop is protected by Windows Winlogon security.", fill=(255, 255, 255))
            draw.text((30, 120), f"Host: {platform.node()} | Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(200, 210, 225))
            draw.text((30, 160), "Telegram Bot, UPnP, Web Server & Services are running 100%.", fill=(0, 230, 118))
            draw.text((30, 200), "Remote control: Use /rd on for RustDesk or /cam for webcam.", fill=(79, 172, 254))
            img.save(str(target_path), format="JPEG", quality=80)
            return target_path
        except Exception as e2:
            logger.error(f"Minimal image save failed: {e2}")
            raise e2

def capture_screenshot() -> tuple[Optional[Path], str]:
    """Capture full desktop screenshot with robust multi-engine fallback and lock detection."""
    Config.ensure_directories()
    filename = f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    file_path = Config.SNAPSHOT_DIR / filename

    # Wake monitor display if in DPMS sleep
    _wake_display_if_possible()

    # 1. Engine 1: MSS (Fastest, multi-monitor safe, DPI-safe)
    try:
        import mss
        with mss.MSS() as sct:
            monitor = sct.monitors[0] if sct.monitors else None
            if monitor and monitor.get("width", 0) > 0 and monitor.get("height", 0) > 0:
                sct_img = sct.grab(monitor)
                from PIL import Image
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                img.save(str(file_path), format="JPEG", quality=85)
                if file_path.exists() and file_path.stat().st_size > 1000:
                    return file_path, "Chụp màn hình thành công."
    except Exception as e:
        logger.debug(f"MSS screenshot engine error: {e}")

    # 2. Engine 2: PIL ImageGrab (all_screens=True)
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=True)
        img.save(str(file_path), format="JPEG", quality=85)
        if file_path.exists() and file_path.stat().st_size > 1000:
            return file_path, "Chụp màn hình thành công."
    except Exception as e:
        logger.debug(f"Pillow all_screens error: {e}")

    # 3. Engine 3: PIL ImageGrab (all_screens=False - Primary display fallback)
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=False)
        img.save(str(file_path), format="JPEG", quality=85)
        if file_path.exists() and file_path.stat().st_size > 1000:
            return file_path, "Chụp màn hình chính thành công."
    except Exception as e:
        logger.debug(f"Pillow primary display error: {e}")

    # 4. Engine 4: Direct Windows GDI via ctypes
    if platform.system().lower() == "windows":
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32

            w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
            h = user32.GetSystemMetrics(1)  # SM_CYSCREEN

            if w > 0 and h > 0:
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

                    if file_path.exists() and file_path.stat().st_size > 1000:
                        return file_path, "Chụp màn hình thành công."
                else:
                    gdi32.SelectObject(hdc_mem, hbm_old)
                    gdi32.DeleteObject(hbm)
                    gdi32.DeleteDC(hdc_mem)
                    user32.ReleaseDC(hwnd, hdc_screen)
        except Exception as e:
            logger.debug(f"Direct Win32 GDI error: {e}")

    # 5. Fallback: If all capture engines fail (workstation locked, Winlogon, or detached session)
    try:
        _generate_locked_screen_image(file_path)
        locked = is_workstation_locked()
        if locked:
            msg = "Màn hình desktop đang bị khóa (Windows Lock Screen). Máy chủ vẫn hoạt động bình thường."
        else:
            msg = "Desktop đang chạy ở chế độ dịch vụ nền (Session 0). Đã tạo thẻ an ninh máy chủ."
        return file_path, msg
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
