"""
VNServerSentinel - Main Application Entrypoint
Orchestrates network tracking, security hooks, power outage monitoring,
and the Telegram command center.
"""

import os
import sys
import time
import signal
import logging
import threading
from datetime import datetime

import requests

from config import Config
import network_upnp
import security_guard
import system_monitor
import telegram_bot
import updater
import web_dashboard
import tray_icon
import desktop_ui

def ensure_admin_elevation():
    """Ensure process runs with Administrator privileges on Windows."""
    if sys.platform == "win32" and "--no-elevate" not in sys.argv:
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            is_admin = False

        if not is_admin:
            try:
                import ctypes
                params = " ".join([f'"{a}"' for a in sys.argv[1:]])
                if getattr(sys, "frozen", False):
                    exe = sys.executable
                    cmd_args = params
                else:
                    exe = sys.executable
                    cmd_args = f'"{sys.argv[0]}" {params}'

                ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, cmd_args, None, 1)
                if ret > 32:
                    sys.exit(0)
            except Exception as e:
                pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Config.DATA_DIR / "sentinel.log", encoding="utf-8") if Config.DATA_DIR.exists() else logging.NullHandler()
    ]
)
logger = logging.getLogger("VNServerSentinel.Main")

class ServerSentinelApp:
    def __init__(self):
        Config.ensure_directories()
        self.running = True
        self.last_wan_ip = None
        self.upnp_mgr = network_upnp.UPnPManager()
        self.bot = telegram_bot.SentinelTelegramBot(self.upnp_mgr)
        self.tray = None

    def start(self):
        logger.info("Starting VNServerSentinel Home Server Guardian...")

        # 1. Validate configuration
        valid, err_msg = Config.validate()
        if not valid:
            logger.warning(f"Configuration Warning: {err_msg}")
            print(f"\n[!] CẢNH BÁO CẤU HÌNH: {err_msg}")
            print("[!] Hãy tạo file .env từ .env.example và điền TELEGRAM_BOT_TOKEN cùng TELEGRAM_ADMIN_CHAT_ID.\n")

        # 2. Check and clear update watchdog flag if we just upgraded
        upgraded_ver = updater.check_and_clear_update_flag()
        if upgraded_ver:
            self.bot.notify_admin(f"🎉 *AUTO-UPDATE THÀNH CÔNG!*\nMáy chủ đã được cập nhật an toàn lên phiên bản `v{upgraded_ver}`.")

        # Clean up any leftover .bak files from previous updates
        try:
            base_dir = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Config.BASE_DIR
            for old_bak in base_dir.glob("*.bak*"):
                try:
                    old_bak.unlink()
                except Exception:
                    pass
        except Exception:
            pass

        # 3. Check power outage / reboot history
        reboot_report = system_monitor.check_power_cut_history()
        self._send_startup_notification(reboot_report)

        # 4. Start Windows Session & Intruder Watcher
        session_watcher = security_guard.SessionWatcher(on_intruder_callback=self.bot.handle_intruder_alert)
        session_watcher.start()

        # 5. Start Telegram Bot Polling thread
        bot_thread = threading.Thread(target=self.bot.run_polling, daemon=True)
        bot_thread.start()

        # 6. Start Built-in Glassmorphic Dashboard Server
        web_dashboard.start_dashboard_server(self.upnp_mgr, port=web_dashboard.DASHBOARD_PORT)

        # 7. Start System Tray Icon
        self.tray = tray_icon.SystemTrayManager(on_exit_callback=lambda: sys.exit(0))
        self.tray.start()

        # 8. Enforce BIOS Power Loss setting (counter dead CMOS battery)
        self._enforce_bios_power_loss()

        # 9. Main Background Periodic Loop (IP tracking, Heartbeat ping) in background thread
        main_loop_thread = threading.Thread(target=self._run_main_loop, daemon=True)
        main_loop_thread.start()

        # 10. Launch Native Desktop Window (PyWebView & Edge WebView2)
        desktop_mgr = desktop_ui.DesktopUIManager.get_instance()
        ui_launched = desktop_mgr.launch(port=web_dashboard.DASHBOARD_PORT, on_exit=lambda: sys.exit(0))

        if not ui_launched:
            logger.info("Running in background / headless mode. Main loop active.")
            while self.running:
                time.sleep(1)

    def _enforce_bios_power_loss(self):
        """Reinforce BIOS Restore on AC Power Loss setting periodically to counter dead CMOS battery."""
        if sys.platform == "win32":
            bios_script = Config.BASE_DIR / "bios_helper.ps1"
            if bios_script.exists():
                try:
                    subprocess.Popen(
                        ["powershell", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(bios_script)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    logger.info("Executed BIOS power loss configuration successfully.")
                except Exception as e:
                    logger.debug(f"BIOS helper auto-run notice: {e}")

    def _send_startup_notification(self, reboot_report: dict):
        """Send comprehensive boot alert to user."""
        net = network_upnp.get_network_info()
        self.last_wan_ip = net["wan_ip"]

        if reboot_report:
            msg = (
                f"⚠️ *MÁY CHỦ VIỆT NAM VỪA KHỞI ĐỘNG LẠI!*\n\n"
                f"⏰ *Thời điểm tắt/sập nguồn:* `{reboot_report['last_seen_str']}`\n"
                f"🚀 *Thời điểm bật lại:* `{reboot_report['reboot_time_str']}`\n"
                f"⏳ *Thời gian gián đoạn (Downtime):* `{reboot_report['downtime_str']}`\n"
                f"🔍 *Nguyên nhân:* {reboot_report['reason']}\n\n"
                f"🌍 *Public IP hiện tại:* `{net['wan_ip']}`\n"
                f"🏠 *Local IP:* `{net['lan_ip']}`"
            )
        else:
            msg = (
                f"🟢 *MÁY CHỦ VIỆT NAM ĐÃ TRỰC TUYẾN!*\n\n"
                f"🖥️ *Thiết bị:* `{net['hostname']} ({net['system']})`\n"
                f"🌍 *Public IP:* `{net['wan_ip']}`\n"
                f"🏠 *Local IP:* `{net['lan_ip']}`\n\n"
                f"👉 Gõ lệnh `/menu` để mở bảng điều khiển từ xa."
            )

        self.bot.notify_admin(msg, keyboard=self.bot.get_main_menu_keyboard())

    def _run_main_loop(self):
        """Main periodic monitoring loop."""
        logger.info(f"Main loop running (Interval: {Config.CHECK_INTERVAL_SECONDS}s)...")
        while self.running:
            try:
                # Ping cloud heartbeat
                if Config.HEARTBEAT_URL:
                    try:
                        requests.get(Config.HEARTBEAT_URL, timeout=10)
                    except Exception as e:
                        logger.debug(f"Heartbeat URL ping error: {e}")

                # Update heartbeat state
                system_monitor.update_heartbeat_state()

                # Check if Public IP has changed
                current_wan_ip = network_upnp.get_public_ip()
                if current_wan_ip and self.last_wan_ip and current_wan_ip != self.last_wan_ip:
                    logger.warning(f"Public IP changed: {self.last_wan_ip} -> {current_wan_ip}")
                    alert_msg = (
                        f"🌐 *CẢNH BÁO: ĐỊA CHỈ IP MẠNG VỪA THAY ĐỔI!*\n\n"
                        f"🔴 IP cũ: `{self.last_wan_ip}`\n"
                        f"🟢 IP mới: `{current_wan_ip}`\n\n"
                        f"💡 _Các dịch vụ Web và Remote Desktop của bạn hãy kết nối bằng IP mới này._"
                    )
                    self.bot.notify_admin(alert_msg)
                    self.last_wan_ip = current_wan_ip
                elif current_wan_ip:
                    self.last_wan_ip = current_wan_ip

            except Exception as e:
                logger.error(f"Error in main loop cycle: {e}")

            time.sleep(Config.CHECK_INTERVAL_SECONDS)

def check_single_instance() -> tuple[bool, any]:
    """
    Ensure only one instance of PcManager runs at a time using a Windows Named Mutex.
    If another instance is already running, returns (False, mutex).
    """
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            ERROR_ALREADY_EXISTS = 183
            mutex_name = "Global\\PcManager_Sentinel_SingleInstance_Mutex"
            mutex = kernel32.CreateMutexW(None, False, mutex_name)
            last_err = kernel32.GetLastError()
            if last_err == ERROR_ALREADY_EXISTS:
                return False, mutex
            return True, mutex
        except Exception as e:
            logger.debug(f"Mutex check note: {e}")
            return True, None
    return True, None

def handle_exit(signum=None, frame=None):
    logger.info("Shutting down PcManager cleanly...")
    if sys.platform == "win32":
        try:
            import subprocess
            subprocess.Popen("taskkill /F /T /IM PcManager.exe", shell=True)
        except Exception:
            pass
    os._exit(0)

if __name__ == "__main__":
    ensure_admin_elevation()

    # Single-Instance Protection: prevent duplicate background tasks, port conflicts & duplicate Telegram bot polling
    is_first_instance, _app_mutex = check_single_instance()
    if not is_first_instance:
        logger.info("PcManager is already running in background. Bringing up active window or web dashboard...")
        if sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = user32.FindWindowW(None, "PcManager - Quản Trị Máy Chủ Từ Xa (Native Client)")
                if not hwnd:
                    hwnd = user32.FindWindowW(None, "PcManager - Quản Trị Máy Chủ Từ Xa (Classic UI)")
                if hwnd:
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    user32.SetForegroundWindow(hwnd)
                    sys.exit(0)
            except Exception:
                pass
        # Fallback: Open web dashboard in default browser and exit second instance cleanly
        import webbrowser
        webbrowser.open(f"http://localhost:{web_dashboard.DASHBOARD_PORT}")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    app = ServerSentinelApp()
    app.start()
