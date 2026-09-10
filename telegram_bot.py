"""
VNServerSentinel - Telegram Bi-directional Interactive Bot
Handles admin commands, button interactions, file upload/download,
and notification dispatching with strict security.
"""

import os
import sys
import time
import json
import logging
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

import requests

from config import Config
import network_upnp
import security_guard
import system_monitor
import file_manager
import updater
import remote_desktop

logger = logging.getLogger("VNServerSentinel.Telegram")

class TelegramClient:
    """Lightweight and robust client for the Telegram Bot API."""
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = requests.Session()

    def send_message(self, chat_id: str, text: str, reply_markup: Optional[Dict] = None, parse_mode: str = "Markdown") -> Optional[Dict]:
        """Send formatted text message with optional inline buttons."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        try:
            r = self.session.post(url, data=payload, timeout=15)
            # If markdown failed due to formatting characters, retry without parse_mode
            if r.status_code == 400 and parse_mode:
                payload.pop("parse_mode")
                r = self.session.post(url, data=payload, timeout=15)
            return r.json()
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return None

    def send_photo(self, chat_id: str, photo_path: Path, caption: str = "") -> Optional[Dict]:
        """Upload and send an image file."""
        url = f"{self.base_url}/sendPhoto"
        try:
            with open(photo_path, "rb") as f:
                files = {"photo": f}
                data = {"chat_id": chat_id, "caption": caption[:1024]}
                r = self.session.post(url, data=data, files=files, timeout=30)
                return r.json()
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return None

    def send_document(self, chat_id: str, doc_path: Path, caption: str = "") -> Optional[Dict]:
        """Upload and send a document/file."""
        url = f"{self.base_url}/sendDocument"
        try:
            with open(doc_path, "rb") as f:
                files = {"document": f}
                data = {"chat_id": chat_id, "caption": caption[:1024]}
                r = self.session.post(url, data=data, files=files, timeout=60)
                return r.json()
        except Exception as e:
            logger.error(f"Error sending document: {e}")
            return None

    def get_file_bytes(self, file_id: str) -> Optional[tuple[bytes, str]]:
        """Download file sent by user."""
        try:
            r = self.session.get(f"{self.base_url}/getFile?file_id={file_id}", timeout=15)
            data = r.json()
            if data.get("ok"):
                file_path = data["result"]["file_path"]
                download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
                file_resp = self.session.get(download_url, timeout=60)
                filename = Path(file_path).name
                return file_resp.content, filename
        except Exception as e:
            logger.error(f"Error downloading file from Telegram: {e}")
        return None

    def answer_callback(self, callback_query_id: str, text: str = ""):
        """Acknowledge button clicks."""
        try:
            self.session.post(
                f"{self.base_url}/answerCallbackQuery",
                data={"callback_query_id": callback_query_id, "text": text},
                timeout=10
            )
        except Exception:
            pass

    def get_updates(self, offset: int = 0, timeout: int = 30) -> List[Dict]:
        """Fetch incoming messages via long polling."""
        url = f"{self.base_url}/getUpdates"
        try:
            r = self.session.get(url, params={"offset": offset, "timeout": timeout}, timeout=timeout + 10)
            data = r.json()
            if data.get("ok"):
                return data.get("result", [])
        except Exception as e:
            logger.debug(f"get_updates polling error: {e}")
        return []


class SentinelTelegramBot:
    """Interactive command & control bot for VNServerSentinel."""
    def __init__(self, upnp_mgr: network_upnp.UPnPManager):
        self.client = TelegramClient(Config.TELEGRAM_BOT_TOKEN)
        self.admin_id = str(Config.TELEGRAM_ADMIN_CHAT_ID)
        self.upnp_mgr = upnp_mgr
        self.running = True
        self.last_update_id = 0

    def get_main_menu_keyboard(self) -> Dict:
        """Create inline keyboard with quick-action buttons."""
        return {
            "inline_keyboard": [
                [
                    {"text": "📊 Trạng Thái Máy", "callback_data": "cmd_status"},
                    {"text": "🌐 Địa Chỉ IP", "callback_data": "cmd_ip"}
                ],
                [
                    {"text": "📸 Chụp Màn Hình", "callback_data": "cmd_screen"},
                    {"text": "📷 Chụp Webcam", "callback_data": "cmd_cam"}
                ],
                [
                    {"text": "🔒 Khóa Máy Ngay", "callback_data": "cmd_lock"},
                    {"text": "🚪 Quản Lý Port", "callback_data": "cmd_ports"}
                ],
                [
                    {"text": "📁 Quản Lý Tệp", "callback_data": "cmd_files"},
                    {"text": "🖥️ Remote Desktop", "callback_data": "cmd_rd"}
                ],
                [
                    {"text": "🔄 Check Update", "callback_data": "cmd_update"}
                ]
            ]
        }

    def notify_admin(self, message: str, keyboard: Optional[Dict] = None):
        """Dispatch high-priority alert to the admin's Telegram."""
        if not self.admin_id:
            return
        self.client.send_message(self.admin_id, message, reply_markup=keyboard)

    def handle_intruder_alert(self, event_data: dict):
        """Dispatched by Security Guard when someone touches/unlocks the physical PC."""
        timestamp = event_data.get("timestamp")
        event_name = event_data.get("event")
        msg = (
            f"🚨 *CẢNH BÁO XÂM NHẬP TẠI NHÀ VIỆT NAM!*\n\n"
            f"⏰ *Thời gian:* `{timestamp}`\n"
            f"👤 *Sự kiện:* `{event_name}`\n"
            f"⚠️ Có ai đó vừa tương tác / mở khóa trực tiếp tại máy chủ!"
        )
        actions_kb = {
            "inline_keyboard": [
                [{"text": "🔒 Khóa Máy Ngay Lập Tức", "callback_data": "cmd_lock"}],
                [{"text": "📸 Chụp Lại Màn Hình", "callback_data": "cmd_screen"},
                 {"text": "📷 Chụp Lại Webcam", "callback_data": "cmd_cam"}]
            ]
        }
        self.notify_admin(msg, keyboard=actions_kb)

        # Send captured photos if available
        if event_data.get("webcam_image") and Path(event_data["webcam_image"]).exists():
            self.client.send_photo(self.admin_id, Path(event_data["webcam_image"]), caption="📷 Ảnh chụp người ngồi trước máy")

        if event_data.get("screen_image") and Path(event_data["screen_image"]).exists():
            self.client.send_photo(self.admin_id, Path(event_data["screen_image"]), caption="🖥️ Ảnh màn hình lúc mở khóa")

    def run_polling(self):
        """Continuous polling loop."""
        logger.info("Telegram Bot polling started...")
        while self.running:
            updates = self.client.get_updates(offset=self.last_update_id + 1, timeout=20)
            for update in updates:
                self.last_update_id = update["update_id"]
                try:
                    if "message" in update:
                        self._process_message(update["message"])
                    elif "callback_query" in update:
                        self._process_callback(update["callback_query"])
                except Exception as e:
                    logger.error(f"Error processing update: {e}")
            time.sleep(1)

    def _is_admin(self, user_id: Any) -> bool:
        """Validate if the sender is the authorized administrator."""
        return str(user_id) == self.admin_id

    def _process_message(self, msg: Dict):
        user_id = msg.get("from", {}).get("id")
        chat_id = str(msg.get("chat", {}).get("id"))
        text = msg.get("text", "").strip()

        if not self._is_admin(user_id):
            logger.warning(f"Unauthorized access attempt from User ID: {user_id}")
            self.client.send_message(chat_id, "⛔ Bạn không có quyền điều khiển máy chủ này.")
            return

        # Check if user sent a file/document to upload to server
        if "document" in msg:
            self._handle_file_upload(msg)
            return

        if not text:
            return

        parts = text.split()
        command = parts[0].lower()
        args = parts[1:]

        if command in ("/start", "/menu", "/help"):
            welcome = (
                "🛡️ *VNServerSentinel - Trung Tâm Điều Khiển Máy Chủ*\n"
                "Máy chủ tại Việt Nam đang trực tuyến và sẵn sàng nhận lệnh!\n\n"
                "Chọn các nút điều khiển bên dưới hoặc gõ lệnh trực tiếp:"
            )
            self.client.send_message(chat_id, welcome, reply_markup=self.get_main_menu_keyboard())

        elif command == "/status":
            self._cmd_status(chat_id)

        elif command == "/ip":
            self._cmd_ip(chat_id)

        elif command == "/screen":
            self._cmd_screen(chat_id)

        elif command == "/cam":
            self._cmd_cam(chat_id)

        elif command == "/lock":
            success, message = security_guard.lock_workstation()
            self.client.send_message(chat_id, message)

        elif command == "/port":
            self._cmd_port(chat_id, args)

        elif command in ("/files", "/dir", "/ls"):
            target_path = " ".join(args) if args else None
            self._cmd_files(chat_id, target_path)

        elif command == "/cat":
            if not args:
                self.client.send_message(chat_id, "⚠️ Cú pháp: `/cat <đường_dẫn_file>`")
                return
            target_path = " ".join(args)
            ok, content = file_manager.read_text_file(target_path)
            self.client.send_message(chat_id, content)

        elif command == "/download":
            if not args:
                self.client.send_message(chat_id, "⚠️ Cú pháp: `/download <đường_dẫn_file>`")
                return
            target_path = Path(" ".join(args))
            if target_path.exists() and target_path.is_file():
                self.client.send_message(chat_id, f"⏳ Đang tải file `{target_path.name}` lên Telegram...")
                self.client.send_document(chat_id, target_path, caption=f"📄 {target_path.name}")
            else:
                self.client.send_message(chat_id, f"❌ File không tồn tại: `{target_path}`")

        elif command == "/mkdir":
            if not args:
                self.client.send_message(chat_id, "⚠️ Cú pháp: `/mkdir <đường_dẫn_thư_mục>`")
                return
            ok, msg_text = file_manager.make_directory(" ".join(args))
            self.client.send_message(chat_id, msg_text)

        elif command == "/rm":
            # Requires PIN: /rm <pin> <path>
            if len(args) < 2:
                self.client.send_message(chat_id, "⚠️ Cú pháp xóa an toàn: `/rm <mã_PIN> <đường_dẫn>`")
                return
            pin, target_path = args[0], " ".join(args[1:])
            if pin != Config.ADMIN_PIN:
                self.client.send_message(chat_id, "❌ Mã PIN không chính xác!")
                return
            ok, msg_text = file_manager.delete_path(target_path)
            self.client.send_message(chat_id, msg_text)

        elif command == "/exec":
            # Requires PIN: /exec <pin> <powershell command>
            if len(args) < 2:
                self.client.send_message(chat_id, "⚠️ Cú pháp chạy lệnh Admin: `/exec <mã_PIN> <lệnh_powershell>`\nVí dụ: `/exec 1234 Get-Service`")
                return
            pin, cmd_to_run = args[0], " ".join(args[1:])
            if pin != Config.ADMIN_PIN:
                self.client.send_message(chat_id, "❌ Mã PIN bảo mật không chính xác!")
                return
            self._cmd_exec(chat_id, cmd_to_run)

        elif command == "/reboot":
            if not args or args[0] != Config.ADMIN_PIN:
                self.client.send_message(chat_id, "⚠️ Khởi động lại yêu cầu mã PIN: `/reboot <mã_PIN>`")
                return
            self.client.send_message(chat_id, "🔄 Đang khởi động lại máy tính Windows trong 5 giây...")
            subprocess.run("shutdown /r /t 5 /f", shell=True)

        elif command == "/shutdown":
            if not args or args[0] != Config.ADMIN_PIN:
                self.client.send_message(chat_id, "⚠️ Tắt máy yêu cầu mã PIN: `/shutdown <mã_PIN>`")
                return
            self.client.send_message(chat_id, "🛑 Đang tắt nguồn máy chủ trong 5 giây...")
            subprocess.run("shutdown /s /t 5 /f", shell=True)

        elif command == "/update":
            sub = args[0].lower() if args else "check"
            if sub == "check":
                self._cmd_update_check(chat_id)
            elif sub == "run":
                self._cmd_update_run(chat_id)

        elif command == "/rd":
            sub = args[0].lower() if args else "status"
            if sub == "on":
                ok, msg = remote_desktop.start_remote_desktop()
                self.client.send_message(chat_id, msg)
            elif sub == "off":
                ok, msg = remote_desktop.stop_remote_desktop()
                self.client.send_message(chat_id, msg)
            else:
                st = remote_desktop.get_remote_desktop_status()
                kb = {
                    "inline_keyboard": [
                        [{"text": "🟢 Bật RustDesk", "callback_data": "rd_on"},
                         {"text": "🛑 Tắt RustDesk", "callback_data": "rd_off"}],
                        [{"text": "🔙 Menu Chính", "callback_data": "cmd_menu"}]
                    ]
                }
                self.client.send_message(chat_id, f"🖥️ *ĐIỀU KHIỂN REMOTE DESKTOP TỪ XA*\n\nTrạng thái: `{st}`\n\n💡 _Dùng `/rd on` khi cần điều khiển màn hình từ Đài Loan, `/rd off` khi dùng xong để tiết kiệm RAM cho máy._", reply_markup=kb)

    def _process_callback(self, cb: Dict):
        """Handle inline button callbacks."""
        cb_id = cb.get("id")
        user_id = cb.get("from", {}).get("id")
        chat_id = str(cb.get("message", {}).get("chat", {}).get("id"))
        data = cb.get("data", "")

        if not self._is_admin(user_id):
            self.client.answer_callback(cb_id, "⛔ Không được phép")
            return

        self.client.answer_callback(cb_id, "Đang xử lý...")

        if data == "cmd_status":
            self._cmd_status(chat_id)
        elif data == "cmd_ip":
            self._cmd_ip(chat_id)
        elif data == "cmd_screen":
            self._cmd_screen(chat_id)
        elif data == "cmd_cam":
            self._cmd_cam(chat_id)
        elif data == "cmd_lock":
            _, msg = security_guard.lock_workstation()
            self.client.send_message(chat_id, msg)
        elif data == "cmd_ports":
            self._cmd_port(chat_id, ["list"])
        elif data == "cmd_files":
            self._cmd_files(chat_id, None)
        elif data == "cmd_update":
            self._cmd_update_check(chat_id)
        elif data == "cmd_rd":
            st = remote_desktop.get_remote_desktop_status()
            kb = {
                "inline_keyboard": [
                    [{"text": "🟢 Bật RustDesk", "callback_data": "rd_on"},
                     {"text": "🛑 Tắt RustDesk", "callback_data": "rd_off"}],
                    [{"text": "🔙 Menu Chính", "callback_data": "cmd_menu"}]
                ]
            }
            self.client.send_message(chat_id, f"🖥️ *QUẢN LÝ REMOTE DESKTOP (ON-DEMAND)*\n\nTrạng thái: `{st}`\n\n_Bật khi cần kết nối, tắt khi xong để tiết kiệm 200MB RAM cho Core i3._", reply_markup=kb)
        elif data == "rd_on":
            ok, msg = remote_desktop.start_remote_desktop()
            self.client.send_message(chat_id, msg)
        elif data == "rd_off":
            ok, msg = remote_desktop.stop_remote_desktop()
            self.client.send_message(chat_id, msg)
        elif data == "cmd_menu":
            self.client.send_message(chat_id, "🛡️ *Menu Điều Khiển Máy Chủ:*", reply_markup=self.get_main_menu_keyboard())

    def _cmd_status(self, chat_id: str):
        stats = system_monitor.get_hardware_status()
        net = network_upnp.get_network_info()

        disk_lines = [f"  • `{d['mount']}` {d['percent']}% (Trống {d['free_gb']}GB / {d['total_gb']}GB)" for d in stats["disks"]]
        user_lines = [f"  • `{u['name']}` ({u['terminal']}) từ {u['started']}" for u in stats["active_users"]] or ["  • Không có phiên đăng nhập trực tiếp"]

        msg = (
            f"📊 *TRẠNG THÁI MÁY CHỦ VIỆT NAM*\n\n"
            f"🖥️ *Hệ thống:* `{net['hostname']} ({net['system']} {net['release']})`\n"
            f"⏱️ *Uptime:* `{stats['uptime']}`\n"
            f"🚀 *Khởi động lúc:* `{stats['boot_time']}`\n\n"
            f"⚙️ *CPU:* `{stats['cpu_percent']}%` ({stats['cpu_count']} Cores)\n"
            f"🧠 *RAM:* `{stats['ram_percent']}%` (`{stats['ram_used_gb']}GB` / `{stats['ram_total_gb']}GB`)\n"
            f"💾 *Ổ Đĩa:*\n" + "\n".join(disk_lines) + "\n\n"
            f"🌐 *Public IP:* `{net['wan_ip']}`\n"
            f"🏠 *Local IP:* `{net['lan_ip']}`\n"
            f"🖥️ *Remote Desktop:* `{remote_desktop.get_remote_desktop_status()}`\n\n"
            f"👥 *Người dùng đang hoạt động:*\n" + "\n".join(user_lines)
        )
        self.client.send_message(chat_id, msg, reply_markup=self.get_main_menu_keyboard())

    def _cmd_ip(self, chat_id: str):
        net = network_upnp.get_network_info()
        msg = (
            f"🌐 *THÔNG TIN ĐỊA CHỈ IP MẠNG*\n\n"
            f"🌍 *Public WAN IP:* `{net['wan_ip']}`\n"
            f"🏠 *Local LAN IP:* `{net['lan_ip']}`\n"
            f"💻 *Hostname:* `{net['hostname']}`\n\n"
            f"💡 _Khi nhà mạng tại VN đổi IP, hệ thống sẽ tự động gửi tin nhắn báo IP mới cho bạn tức thì!_"
        )
        self.client.send_message(chat_id, msg)

    def _cmd_screen(self, chat_id: str):
        self.client.send_message(chat_id, "⏳ Đang chụp màn hình desktop...")
        img_path, msg = security_guard.capture_screenshot()
        if img_path and img_path.exists():
            self.client.send_photo(chat_id, img_path, caption=f"🖥️ Màn hình Desktop lúc {datetime.now().strftime('%H:%M:%S')}")
        else:
            self.client.send_message(chat_id, f"❌ {msg}")

    def _cmd_cam(self, chat_id: str):
        self.client.send_message(chat_id, "⏳ Đang kích hoạt webcam chụp ảnh...")
        img_path, msg = security_guard.capture_webcam()
        if img_path and img_path.exists():
            self.client.send_photo(chat_id, img_path, caption=f"📷 Ảnh Webcam lúc {datetime.now().strftime('%H:%M:%S')}")
        else:
            self.client.send_message(chat_id, f"❌ {msg}")

    def _cmd_port(self, chat_id: str, args: List[str]):
        if not args or args[0].lower() == "list":
            mappings = self.upnp_mgr.list_ports()
            if mappings:
                lines = [f"• Ext `{m.get('external_port')}` ➔ Int `{m.get('internal_port')}` ({m.get('protocol')}) - {m.get('description', '')}" for m in mappings]
                res = "🚪 *DANH SÁCH PORT ĐANG MỞ TRÊN ROUTER:*\n\n" + "\n".join(lines)
            else:
                res = (
                    "🚪 *HƯỚNG DẪN QUẢN LÝ PORT TỪ XA:*\n\n"
                    "• *Mở port:* `/port open <port_ngoài> <port_trong> [TCP/UDP]`\n"
                    "  _Ví dụ:_ `/port open 8080 8080 TCP`\n\n"
                    "• *Đóng port:* `/port close <port_ngoài> [TCP/UDP]`\n"
                    "  _Ví dụ:_ `/port close 8080 TCP`\n\n"
                    "• *Xem danh sách:* `/port list`"
                )
            self.client.send_message(chat_id, res)
            return

        action = args[0].lower()
        if action == "open":
            if len(args) < 3:
                self.client.send_message(chat_id, "⚠️ Cú pháp: `/port open <port_ngoài> <port_trong> [TCP/UDP]`")
                return
            ext_p = int(args[1])
            int_p = int(args[2])
            proto = args[3].upper() if len(args) > 3 else "TCP"
            ok, msg = self.upnp_mgr.open_port(ext_p, int_p, protocol=proto)
            wan = network_upnp.get_public_ip()
            if ok:
                msg += f"\n\n🔗 Link truy cập trực tiếp: `http://{wan}:{ext_p}`"
            self.client.send_message(chat_id, msg)

        elif action == "close":
            if len(args) < 2:
                self.client.send_message(chat_id, "⚠️ Cú pháp: `/port close <port_ngoài> [TCP/UDP]`")
                return
            ext_p = int(args[1])
            proto = args[2].upper() if len(args) > 2 else "TCP"
            ok, msg = self.upnp_mgr.close_port(ext_p, protocol=proto)
            self.client.send_message(chat_id, msg)

    def _cmd_files(self, chat_id: str, target_path: Optional[str]):
        ok, data, err_msg = file_manager.list_directory(target_path)
        if not ok:
            self.client.send_message(chat_id, f"❌ {err_msg}")
            return

        curr = data["current_path"]
        items = data["items"]
        lines = []
        for it in items[:35]:
            lines.append(f"{it['name']}  `{it['size']}`")

        text = f"📁 *THƯ MỤC:* `{curr}`\n\n" + ("\n".join(lines) or "_Thư mục trống_")
        text += "\n\n💡 _Dùng lệnh `/files <path>` để mở thư mục, `/cat <file>` để đọc, `/download <file>` để tải về._"
        self.client.send_message(chat_id, text)

    def _handle_file_upload(self, msg: Dict):
        chat_id = str(msg.get("chat", {}).get("id"))
        doc = msg["document"]
        file_id = doc.get("file_id")
        raw_name = doc.get("file_name", "uploaded_file")
        caption = msg.get("caption", "").strip()

        target_dir = caption if (caption and Path(caption).is_dir()) else str(Config.DATA_DIR / "uploads")
        self.client.send_message(chat_id, f"⏳ Đang lưu tệp `{raw_name}` vào máy chủ...")

        res = self.client.get_file_bytes(file_id)
        if res:
            content, _ = res
            ok, save_msg = file_manager.save_uploaded_file(content, target_dir, raw_name)
            self.client.send_message(chat_id, save_msg)
        else:
            self.client.send_message(chat_id, "❌ Không thể tải file từ Telegram.")

    def _cmd_exec(self, chat_id: str, cmd: str):
        self.client.send_message(chat_id, f"⏳ Đang thực thi lệnh Admin:\n`{cmd}`")
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd] if platform.system().lower() == "windows" else ["bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            out = res.stdout.strip()
            err = res.stderr.strip()
            result = out or err or "[Lệnh thực thi thành công không có output]"
            if len(result) > 3800:
                result = result[:3800] + "\n...(Kết quả quá dài đã được rút gọn)"
            self.client.send_message(chat_id, f"```powershell\n{result}\n```")
        except subprocess.TimeoutExpired:
            self.client.send_message(chat_id, "⚠️ Lệnh vượt quá thời gian chờ (30 giây)!")
        except Exception as e:
            self.client.send_message(chat_id, f"❌ Lỗi thực thi: {e}")

    def _cmd_update_check(self, chat_id: str):
        curr = updater.get_current_version()
        self.client.send_message(chat_id, f"🔍 Đang kiểm tra GitHub Releases (Bản hiện tại: `v{curr}`)...")
        has_up, new_v, dl_url, notes = updater.check_github_update()
        if has_up:
            msg = (
                f"🎉 *PHÁT HIỆN PHIÊN BẢN MỚI: v{new_v}!*\n\n"
                f"📝 *Ghi chú cập nhật:*\n{notes}\n\n"
                f"👉 Gõ lệnh `/update run` để tự động nâng cấp (có cơ chế Safe-Rollback an toàn)!"
            )
            self.client.send_message(chat_id, msg)
        else:
            self.client.send_message(chat_id, f"✅ {notes} (Phiên bản: `v{curr}`)")

    def _cmd_update_run(self, chat_id: str):
        has_up, new_v, dl_url, _ = updater.check_github_update()
        if not has_up or not dl_url:
            self.client.send_message(chat_id, "✅ Không có bản cập nhật mới nào để tải.")
            return

        self.client.send_message(chat_id, f"⏳ Đang tải bản cập nhật `v{new_v}` từ GitHub và tạo bản sao lưu an toàn...")
        try:
            zip_dest = Config.STAGING_DIR / f"update_v{new_v}.zip"
            Config.ensure_directories()
            
            # Download file
            req = requests.get(dl_url, stream=True, timeout=60)
            with open(zip_dest, "wb") as f:
                for chunk in req.iter_content(chunk_size=8192):
                    f.write(chunk)

            ok, apply_msg = updater.apply_update_from_zip(zip_dest, new_v)
            self.client.send_message(chat_id, apply_msg)

            if ok:
                # Restart process
                self.client.send_message(chat_id, "🔄 Khởi động lại ứng dụng với phiên bản mới...")
                python = sys.executable
                os.execl(python, python, *sys.argv)
        except Exception as e:
            self.client.send_message(chat_id, f"❌ Lỗi trong quá trình cập nhật: {e}")
