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

        # 3. Check power outage / reboot history
        reboot_report = system_monitor.check_power_cut_history()
        self._send_startup_notification(reboot_report)

        # 4. Start Windows Session & Intruder Watcher
        session_watcher = security_guard.SessionWatcher(on_intruder_callback=self.bot.handle_intruder_alert)
        session_watcher.start()

        # 5. Start Telegram Bot Polling thread
        bot_thread = threading.Thread(target=self.bot.run_polling, daemon=True)
        bot_thread.start()

        # 6. Enforce BIOS Power Loss setting (counter dead CMOS battery)
        self._enforce_bios_power_loss()

        # 7. Main Background Periodic Loop (IP tracking, Heartbeat ping)
        self._run_main_loop()

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
                f"🏠 *Local IP:* `{net['lan_ip']}`\n"
                f"⏱️ *Khởi động:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
                f"🛡️ _Hệ thống giám sát vật lý, mạng UPnP và Telegram Bot đang chạy._"
            )

        self.bot.notify_admin(msg, keyboard=self.bot.get_main_menu_keyboard())

    def _run_main_loop(self):
        """Periodic background checks for IP changes and external heartbeats."""
        logger.info("Entering background monitoring loop...")
        while self.running:
            try:
                # Update heartbeat state
                system_monitor.update_heartbeat_state()

                # Ping Cloud Dead-Man's switch if configured
                if Config.HEARTBEAT_URL:
                    try:
                        requests.get(Config.HEARTBEAT_URL, timeout=10)
                    except Exception as e:
                        logger.debug(f"Heartbeat URL ping error: {e}")

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

def handle_exit(signum, frame):
    logger.info("Shutting down VNServerSentinel gracefully...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    app = ServerSentinelApp()
    app.start()
