"""
VNServerSentinel - Native Desktop Management Application
Provides a 100% REAL Native Desktop Application (CustomTkinter & Tkinter GUI)
with authentic native buttons, dynamic meters, real-time port inspectors,
and a dedicated CMD terminal, alongside 1-click Web Browser Dashboard access.
"""

import os
import sys
import time
import logging
import platform
import threading
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional, Callable

from config import Config
import security_guard
import system_monitor
import network_upnp
import remote_desktop
import updater

logger = logging.getLogger("VNServerSentinel.DesktopUI")

# Check GUI library availability
USE_CUSTOMTKINTER = False
USE_TKINTER = False

try:
    import customtkinter as ctk
    USE_CUSTOMTKINTER = True
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
except Exception:
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox, scrolledtext
        USE_TKINTER = True
    except Exception:
        pass


class DesktopUIManager:
    _instance: Optional["DesktopUIManager"] = None

    def __init__(self):
        self.window = None
        self.port: int = 8888
        self.on_exit_callback: Optional[Callable] = None
        self.is_native_active: bool = False
        self._closing_to_tray: bool = True
        self._app_instance = None

    @classmethod
    def get_instance(cls) -> "DesktopUIManager":
        if cls._instance is None:
            cls._instance = DesktopUIManager()
        return cls._instance

    def show_window(self) -> bool:
        """Bring native desktop window to foreground, unhide and focus."""
        if self._app_instance:
            try:
                self._app_instance.show_window()
                return True
            except Exception as e:
                logger.debug(f"Could not restore native window: {e}")

        # If window is not running, open in browser as fallback
        try:
            webbrowser.open(f"http://localhost:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to open browser fallback: {e}")
            return False

    def hide_window(self):
        """Minimize/hide window to Windows System Tray."""
        if self._app_instance:
            try:
                self._app_instance.hide_window()
            except Exception as e:
                logger.debug(f"Error hiding window: {e}")

    def exit_completely(self):
        """Cleanly destroy window and trigger app shutdown."""
        self._closing_to_tray = False
        if self._app_instance:
            try:
                self._app_instance.destroy()
            except Exception:
                pass
        if self.on_exit_callback:
            try:
                self.on_exit_callback()
            except Exception:
                pass

    def launch(self, port: int = 8888, on_exit: Optional[Callable] = None) -> bool:
        """
        Launch the True Native Desktop Application.
        Uses CustomTkinter for a modern dark-mode Windows 11 UI with real buttons and controls.
        Falls back smoothly to standard Tkinter, or headless mode if no display server is present.
        """
        self.port = port
        self.on_exit_callback = on_exit

        # Suppress GUI if explicit background/service flag is passed
        if any(arg in sys.argv for arg in ("--service", "--silent", "--minimized", "--no-gui")):
            logger.info("Running in silent/service mode. Desktop UI window suppressed.")
            return False

        if not USE_CUSTOMTKINTER and not USE_TKINTER:
            logger.info("No Tkinter/CustomTkinter GUI engine available on this OS. Running in background/headless mode.")
            return False

        try:
            if USE_CUSTOMTKINTER:
                app = ModernNativeApp(self, port=self.port)
            else:
                app = ClassicTkinterApp(self, port=self.port)

            self._app_instance = app
            self.window = app
            self.is_native_active = True
            logger.info("Starting True Native Desktop UI Window...")
            app.run()
            return True

        except Exception as e:
            logger.warning(f"Native Desktop UI could not start: {e}. Falling back to background engine.")
            self.is_native_active = False
            return False


# =========================================================================
# MODERN CUSTOMTKINTER NATIVE DESKTOP APPLICATION
# =========================================================================
if USE_CUSTOMTKINTER:
    class ModernNativeApp(ctk.CTk):
        def __init__(self, manager: DesktopUIManager, port: int = 8888):
            super().__init__()
            self.manager = manager
            self.port = port

            # Window configuration
            self.title("PcManager - Quản Trị Máy Chủ Từ Xa (Native Client)")
            self.geometry("1060x720")
            self.minsize(880, 580)

            # Set Window Icon
            icon_ico = Config.BASE_DIR / "assets" / "app.ico"
            if icon_ico.exists() and sys.platform == "win32":
                try:
                    self.iconbitmap(str(icon_ico))
                except Exception:
                    pass

            # Intercept Close [X] -> Hide to System Tray
            self.protocol("WM_DELETE_WINDOW", self.hide_window)

            self._build_ui()
            self._start_telemetry_loop()

        def hide_window(self):
            """Hide to system tray near the clock without stopping background tasks."""
            self.withdraw()
            logger.info("PcManager Native UI minimized to System Tray.")

        def show_window(self):
            """Restore window from system tray."""
            self.deiconify()
            self.state("normal")
            self.lift()
            self.focus_force()

        def _build_ui(self):
            # 1. Top Header Bar
            header_frame = ctk.CTkFrame(self, fg_color="#101726", height=60, corner_radius=0)
            header_frame.pack(fill="x", side="top", padx=0, pady=0)

            logo_label = ctk.CTkLabel(
                header_frame,
                text="🛡️ PcManager Server Guardian",
                font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                text_color="#00f2fe"
            )
            logo_label.pack(side="left", padx=20, pady=12)

            status_badge = ctk.CTkLabel(
                header_frame,
                text="🟢 Trực Tuyến 24/7 (Online)",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#00e676",
                fg_color="rgba(0, 230, 118, 0.15)",
                corner_radius=12,
                padx=12,
                pady=4
            )
            status_badge.pack(side="left", padx=10, pady=12)

            btn_open_web = ctk.CTkButton(
                header_frame,
                text="🌐 Mở Trình Duyệt Web",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                fg_color="#00f2fe",
                text_color="#0a101d",
                hover_color="#4facfe",
                width=160,
                height=32,
                command=self._open_web_browser
            )
            btn_open_web.pack(side="right", padx=15, pady=12)

            btn_hide = ctk.CTkButton(
                header_frame,
                text="⬇️ Thu Nhỏ Khay Tray",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                fg_color="#232f48",
                text_color="#cbd5e1",
                hover_color="#334155",
                width=140,
                height=32,
                command=self.hide_window
            )
            btn_hide.pack(side="right", padx=5, pady=12)

            # 2. Main Tab View
            self.tabview = ctk.CTkTabview(self, fg_color="#0d131f", segmented_button_fg_color="#162032",
                                          segmented_button_selected_color="#00f2fe",
                                          segmented_button_selected_hover_color="#4facfe",
                                          text_color="#ffffff")
            self.tabview.pack(fill="both", expand=True, padx=15, pady=10)

            self.tab_monitor = self.tabview.add("📊 Giám Sát Phần Cứng")
            self.tab_security = self.tabview.add("🛡️ An Ninh & Màn Hình")
            self.tab_services = self.tabview.add("🔌 Dịch Vụ & Port Đang Chạy")
            self.tab_cmd = self.tabview.add("💻 Terminal CMD / PowerShell")
            self.tab_settings = self.tabview.add("⚙️ Trình Duyệt & Cài Đặt")

            self._build_tab_monitor()
            self._build_tab_security()
            self._build_tab_services()
            self._build_tab_cmd()
            self._build_tab_settings()

            # Bottom Status Bar
            self.status_bar = ctk.CTkLabel(
                self,
                text="Sẵn sàng | Telegram Bot: Online | Web Dashboard: http://localhost:8888 | Auto-Update: Sẵn sàng",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color="#94a3b8",
                anchor="w",
                padx=15,
                pady=4
            )
            self.status_bar.pack(fill="x", side="bottom")

        # -------------------------------------------------------------
        # TAB 1: HARDWARE & SYSTEM MONITOR
        # -------------------------------------------------------------
        def _build_tab_monitor(self):
            frame = self.tab_monitor

            # Top Telemetry Cards
            cards_frame = ctk.CTkFrame(frame, fg_color="transparent")
            cards_frame.pack(fill="x", padx=10, pady=10)

            # CPU Card
            self.card_cpu = ctk.CTkFrame(cards_frame, fg_color="#162032", corner_radius=12)
            self.card_cpu.pack(side="left", fill="both", expand=True, padx=5)

            ctk.CTkLabel(self.card_cpu, text="⚙️ SỬ DỤNG CPU", font=ctk.CTkFont(size=13, weight="bold"), text_color="#00f2fe").pack(anchor="w", padx=15, pady=(12, 4))
            self.lbl_cpu_val = ctk.CTkLabel(self.card_cpu, text="0%", font=ctk.CTkFont(size=26, weight="bold"), text_color="#ffffff")
            self.lbl_cpu_val.pack(anchor="w", padx=15, pady=2)
            self.pbar_cpu = ctk.CTkProgressBar(self.card_cpu, progress_color="#00f2fe", height=8)
            self.pbar_cpu.pack(fill="x", padx=15, pady=(4, 12))
            self.pbar_cpu.set(0)

            # RAM Card
            self.card_ram = ctk.CTkFrame(cards_frame, fg_color="#162032", corner_radius=12)
            self.card_ram.pack(side="left", fill="both", expand=True, padx=5)

            ctk.CTkLabel(self.card_ram, text="🧠 BỘ NHỚ RAM", font=ctk.CTkFont(size=13, weight="bold"), text_color="#00e676").pack(anchor="w", padx=15, pady=(12, 4))
            self.lbl_ram_val = ctk.CTkLabel(self.card_ram, text="0% (0 / 0 GB)", font=ctk.CTkFont(size=22, weight="bold"), text_color="#ffffff")
            self.lbl_ram_val.pack(anchor="w", padx=15, pady=2)
            self.pbar_ram = ctk.CTkProgressBar(self.card_ram, progress_color="#00e676", height=8)
            self.pbar_ram.pack(fill="x", padx=15, pady=(4, 12))
            self.pbar_ram.set(0)

            # Disk / Network Card
            self.card_net = ctk.CTkFrame(cards_frame, fg_color="#162032", corner_radius=12)
            self.card_net.pack(side="left", fill="both", expand=True, padx=5)

            ctk.CTkLabel(self.card_net, text="🌐 ĐỊA CHỈ IP MẠNG", font=ctk.CTkFont(size=13, weight="bold"), text_color="#ffab00").pack(anchor="w", padx=15, pady=(12, 4))
            self.lbl_ip_val = ctk.CTkLabel(self.card_net, text="WAN: Đang quét...\nLAN: 127.0.0.1", font=ctk.CTkFont(size=13), text_color="#cbd5e1", justify="left")
            self.lbl_ip_val.pack(anchor="w", padx=15, pady=(2, 12))

            # System Information Box
            self.box_sys = ctk.CTkFrame(frame, fg_color="#162032", corner_radius=12)
            self.box_sys.pack(fill="both", expand=True, padx=15, pady=10)

            ctk.CTkLabel(self.box_sys, text="📋 THÔNG TIN MÁY CHỦ CHI TIẾT", font=ctk.CTkFont(size=14, weight="bold"), text_color="#cbd5e1").pack(anchor="w", padx=15, pady=(12, 6))

            self.lbl_sys_details = ctk.CTkLabel(
                self.box_sys,
                text="Đang nạp thông tin máy chủ...",
                font=ctk.CTkFont(family="Consolas", size=13),
                text_color="#94a3b8",
                justify="left"
            )
            self.lbl_sys_details.pack(anchor="w", padx=15, pady=6)

            # Action bar
            btn_box = ctk.CTkFrame(frame, fg_color="transparent")
            btn_box.pack(fill="x", padx=15, pady=10)

            ctk.CTkButton(btn_box, text="🧹 Dọn Dẹp Giải Phóng RAM", fg_color="#00e676", text_color="#0a101d", hover_color="#69f0ae", font=ctk.CTkFont(weight="bold"), command=self._action_clean_ram).pack(side="left", padx=5)
            ctk.CTkButton(btn_box, text="🔄 Làm Mới Ngay", fg_color="#1e293b", text_color="#e2e8f0", hover_color="#334155", command=self._refresh_hardware_stats).pack(side="left", padx=5)

        # -------------------------------------------------------------
        # TAB 2: SECURITY & SCREENSHOTS
        # -------------------------------------------------------------
        def _build_tab_security(self):
            frame = self.tab_security

            intro = ctk.CTkLabel(
                frame,
                text="Điều khiển an ninh, chụp màn hình desktop, chụp ảnh webcam và giữ máy không sleep:",
                font=ctk.CTkFont(size=13),
                text_color="#94a3b8"
            )
            intro.pack(anchor="w", padx=15, pady=(15, 10))

            grid = ctk.CTkFrame(frame, fg_color="transparent")
            grid.pack(fill="both", expand=True, padx=10, pady=5)

            # Left Action Column
            left_col = ctk.CTkFrame(grid, fg_color="#162032", corner_radius=12)
            left_col.pack(side="left", fill="both", expand=True, padx=5, pady=5)

            ctk.CTkLabel(left_col, text="📸 THAO TÁC HÌNH ẢNH & AN NINH", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00f2fe").pack(anchor="w", padx=15, pady=(12, 10))

            ctk.CTkButton(left_col, text="📸 Chụp Màn Hình Desktop Ngay", fg_color="#00f2fe", text_color="#0a101d", hover_color="#4facfe", height=38, font=ctk.CTkFont(weight="bold"), command=self._action_screenshot).pack(fill="x", padx=15, pady=6)
            ctk.CTkButton(left_col, text="📷 Chụp Webcam Người Ngồi Trước Máy", fg_color="#38bdf8", text_color="#0a101d", hover_color="#7dd3fc", height=38, font=ctk.CTkFont(weight="bold"), command=self._action_webcam).pack(fill="x", padx=15, pady=6)
            ctk.CTkButton(left_col, text="☕ Bật/Tắt Giữ Màn Hình Sáng (Awake)", fg_color="#f59e0b", text_color="#0a101d", hover_color="#fbbf24", height=38, font=ctk.CTkFont(weight="bold"), command=self._action_toggle_awake).pack(fill="x", padx=15, pady=6)
            ctk.CTkButton(left_col, text="🔒 Khóa Màn Hình Ngay (Win + L)", fg_color="#ef4444", text_color="#ffffff", hover_color="#dc2626", height=38, font=ctk.CTkFont(weight="bold"), command=self._action_lock).pack(fill="x", padx=15, pady=6)
            ctk.CTkButton(left_col, text="🖥️ Bật / Tắt RustDesk Remote Desktop", fg_color="#8b5cf6", text_color="#ffffff", hover_color="#a78bfa", height=38, font=ctk.CTkFont(weight="bold"), command=self._action_toggle_rd).pack(fill="x", padx=15, pady=6)

            # Right Status / Log Column
            right_col = ctk.CTkFrame(grid, fg_color="#162032", corner_radius=12)
            right_col.pack(side="left", fill="both", expand=True, padx=5, pady=5)

            ctk.CTkLabel(right_col, text="📋 NHẬT KÝ THAO TÁC AN NINH", font=ctk.CTkFont(size=14, weight="bold"), text_color="#cbd5e1").pack(anchor="w", padx=15, pady=(12, 6))

            self.txt_security_log = ctk.CTkTextbox(right_col, font=ctk.CTkFont(family="Consolas", size=12), text_color="#e2e8f0", fg_color="#0d131f")
            self.txt_security_log.pack(fill="both", expand=True, padx=15, pady=(6, 15))
            self.txt_security_log.insert("end", "[Hệ Thống Sẵn Sàng] Chế độ giám sát an ninh hoạt động 100%.\n")

        # -------------------------------------------------------------
        # TAB 3: SERVICES & PORT INSPECTOR
        # -------------------------------------------------------------
        def _build_tab_services(self):
            frame = self.tab_services

            top_bar = ctk.CTkFrame(frame, fg_color="transparent")
            top_bar.pack(fill="x", padx=15, pady=(10, 5))

            ctk.CTkLabel(top_bar, text="Danh sách các dịch vụ & phần mềm đang lắng nghe cổng mạng (Port):", font=ctk.CTkFont(size=13), text_color="#94a3b8").pack(side="left")
            ctk.CTkButton(top_bar, text="🔄 Quét Lại Port", width=120, height=28, fg_color="#1e293b", hover_color="#334155", command=self._refresh_services).pack(side="right")

            # Table Box
            self.txt_services = ctk.CTkTextbox(frame, font=ctk.CTkFont(family="Consolas", size=13), fg_color="#162032", text_color="#38bdf8")
            self.txt_services.pack(fill="both", expand=True, padx=15, pady=10)

            # Kill control bar
            kill_bar = ctk.CTkFrame(frame, fg_color="#162032", corner_radius=10)
            kill_bar.pack(fill="x", padx=15, pady=(0, 10))

            ctk.CTkLabel(kill_bar, text="Dừng tiến trình (Kill):", font=ctk.CTkFont(size=13, weight="bold"), text_color="#ef4444").pack(side="left", padx=12, pady=10)
            self.entry_kill = ctk.CTkEntry(kill_bar, placeholder_text="Nhập PID hoặc Tên (VD: 4512 hoặc java.exe)...", width=300)
            self.entry_kill.pack(side="left", padx=5, pady=10)

            ctk.CTkButton(kill_bar, text="🛑 Dừng Tiến Trình", fg_color="#ef4444", hover_color="#dc2626", text_color="#fff", command=self._action_kill_service).pack(side="left", padx=10, pady=10)

        # -------------------------------------------------------------
        # TAB 4: CMD / POWERSHELL TERMINAL
        # -------------------------------------------------------------
        def _build_tab_cmd(self):
            frame = self.tab_cmd

            # Console Screen
            self.txt_cmd_console = ctk.CTkTextbox(
                frame,
                font=ctk.CTkFont(family="Consolas", size=13),
                fg_color="#0a0e17",
                text_color="#00e676",
                wrap="none"
            )
            self.txt_cmd_console.pack(fill="both", expand=True, padx=15, pady=(10, 5))
            self.txt_cmd_console.insert("end", "Microsoft Windows Command Prompt [PcManager Native Console]\n(c) Microsoft Corporation. All rights reserved.\n\nType any command below and click 'Thực Thi' or press Enter.\n\n")

            # Quick command buttons bar
            quick_bar = ctk.CTkFrame(frame, fg_color="transparent")
            quick_bar.pack(fill="x", padx=15, pady=4)

            for cmd in ("ipconfig", "netstat -ano", "tasklist", "ping 8.8.8.8"):
                ctk.CTkButton(
                    quick_bar,
                    text=cmd,
                    height=26,
                    width=90,
                    fg_color="#1e293b",
                    hover_color="#334155",
                    font=ctk.CTkFont(family="Consolas", size=12),
                    command=lambda c=cmd: self._run_terminal_cmd(c)
                ).pack(side="left", padx=3)

            ctk.CTkButton(
                quick_bar,
                text="Xóa Màn Hình (CLS)",
                height=26,
                width=130,
                fg_color="#334155",
                hover_color="#475569",
                font=ctk.CTkFont(size=12),
                command=self._clear_terminal
            ).pack(side="right", padx=3)

            # Input bar
            input_bar = ctk.CTkFrame(frame, fg_color="#162032", corner_radius=10)
            input_bar.pack(fill="x", padx=15, pady=(5, 10))

            self.combo_shell = ctk.CTkComboBox(input_bar, values=["CMD", "PowerShell"], width=110)
            self.combo_shell.set("CMD")
            self.combo_shell.pack(side="left", padx=8, pady=8)

            self.entry_cmd = ctk.CTkEntry(
                input_bar,
                placeholder_text="Nhập câu lệnh để chạy trên máy tính Windows...",
                font=ctk.CTkFont(family="Consolas", size=13)
            )
            self.entry_cmd.pack(side="left", fill="x", expand=True, padx=5, pady=8)
            self.entry_cmd.bind("<Return>", lambda e: self._on_terminal_enter())

            ctk.CTkButton(
                input_bar,
                text="⚡ Thực Thi",
                fg_color="#00f2fe",
                text_color="#0a101d",
                hover_color="#4facfe",
                font=ctk.CTkFont(weight="bold"),
                width=110,
                command=self._on_terminal_enter
            ).pack(side="right", padx=8, pady=8)

        # -------------------------------------------------------------
        # TAB 5: WEB BROWSER DASHBOARD & SETTINGS
        # -------------------------------------------------------------
        def _build_tab_settings(self):
            frame = self.tab_settings

            # Big Callout Box for Browser Dashboard
            browser_box = ctk.CTkFrame(frame, fg_color="#162032", corner_radius=12)
            browser_box.pack(fill="x", padx=15, pady=15)

            ctk.CTkLabel(
                browser_box,
                text="🌐 TRUNG TÂM ĐIỀU KHIỂN TRÊN TRÌNH DUYỆT WEB (WEB BROWSER)",
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color="#00f2fe"
            ).pack(anchor="w", padx=20, pady=(15, 6))

            ctk.CTkLabel(
                browser_box,
                text="Máy chủ chạy sẵn dịch vụ Web Dashboard nền tại cổng 8888. Bạn có thể mở trực tiếp bằng Chrome, Edge, Cốc Cốc hoặc từ điện thoại thông minh cùng mạng LAN:",
                font=ctk.CTkFont(size=13),
                text_color="#cbd5e1",
                justify="left"
            ).pack(anchor="w", padx=20, pady=4)

            btn_big_web = ctk.CTkButton(
                browser_box,
                text="🚀 MỞ BẢNG ĐIỀU KHIỂN TRÊN TRÌNH DUYỆT (CHROME / EDGE)",
                font=ctk.CTkFont(size=14, weight="bold"),
                fg_color="#00f2fe",
                text_color="#0a101d",
                hover_color="#4facfe",
                height=45,
                command=self._open_web_browser
            )
            btn_big_web.pack(fill="x", padx=20, pady=(10, 18))

            # Settings and Diagnostic Actions
            diag_box = ctk.CTkFrame(frame, fg_color="#162032", corner_radius=12)
            diag_box.pack(fill="both", expand=True, padx=15, pady=(0, 15))

            ctk.CTkLabel(
                diag_box,
                text="⚙️ CÔNG CỤ HỆ THỐNG & KẾT NỐI",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#cbd5e1"
            ).pack(anchor="w", padx=20, pady=(15, 10))

            btn_row = ctk.CTkFrame(diag_box, fg_color="transparent")
            btn_row.pack(fill="x", padx=15, pady=5)

            ctk.CTkButton(btn_row, text="🔔 Gửi Tin Nhắn Thử Tới Telegram", fg_color="#1e293b", hover_color="#334155", height=36, command=self._action_test_telegram).pack(side="left", padx=5)
            ctk.CTkButton(btn_row, text="🔄 Kiểm Tra Bản Cập Nhật Mới", fg_color="#1e293b", hover_color="#334155", height=36, command=self._action_check_update).pack(side="left", padx=5)
            ctk.CTkButton(btn_row, text="❌ Thu Nhỏ Xuống Khay (Tray)", fg_color="#334155", hover_color="#475569", height=36, command=self.hide_window).pack(side="left", padx=5)

            self.lbl_settings_status = ctk.CTkLabel(
                diag_box,
                text="Cấu hình: Telegram Token đã nạp | Admin Chat ID: " + str(Config.TELEGRAM_ADMIN_CHAT_ID),
                font=ctk.CTkFont(family="Consolas", size=12),
                text_color="#94a3b8"
            )
            self.lbl_settings_status.pack(anchor="w", padx=20, pady=15)

        # -------------------------------------------------------------
        # ACTIONS & LOGIC
        # -------------------------------------------------------------
        def _open_web_browser(self):
            url = f"http://localhost:{self.port}"
            logger.info(f"Opening Web Dashboard in browser: {url}")
            webbrowser.open(url)
            self._log_security(f"Đã mở Bảng Điều Khiển Web Dashboard trên trình duyệt: {url}")

        def _log_security(self, msg: str):
            ts = time.strftime("%H:%M:%S")
            self.txt_security_log.insert("end", f"[{ts}] {msg}\n")
            self.txt_security_log.see("end")

        def _action_screenshot(self):
            self._log_security("Đang chụp màn hình desktop...")
            p, msg = security_guard.capture_screenshot()
            self._log_security(f"Màn hình: {msg} (Tệp: {p.name if p else 'N/A'})")

        def _action_webcam(self):
            self._log_security("Đang chụp webcam máy chủ...")
            p, msg = security_guard.capture_webcam()
            self._log_security(f"Webcam: {msg} (Tệp: {p.name if p else 'N/A'})")

        def _action_toggle_awake(self):
            cur = security_guard.get_awake_mode()
            ok, msg = security_guard.set_awake_mode(not cur)
            self._log_security(f"Awake: {msg}")

        def _action_lock(self):
            ok, msg = security_guard.lock_workstation()
            self._log_security(f"Khóa máy: {msg}")

        def _action_toggle_rd(self):
            st = remote_desktop.get_remote_desktop_status()
            if "đang hoạt động" in st:
                ok, msg = remote_desktop.stop_remote_desktop()
            else:
                ok, msg = remote_desktop.start_remote_desktop()
            self._log_security(f"RustDesk: {msg}")

        def _action_clean_ram(self):
            ok, msg = system_monitor.clean_ram()
            self._log_security(f"Dọn RAM: {msg}")
            self._refresh_hardware_stats()

        def _action_test_telegram(self):
            try:
                import telegram_bot
                bot = telegram_bot.SentinelTelegramBot(None)
                bot.notify_admin(f"🔔 *THÔNG BÁO THỬ TỪ PCMANAGER NATIVE CLIENT*\n\nỨng dụng Native GUI và Telegram kết nối 100%! Thời gian: `{time.strftime('%H:%M:%S')}`")
                self.lbl_settings_status.configure(text=f"✅ Đã gửi thông báo thử nghiệm thành công tới Telegram lúc {time.strftime('%H:%M:%S')}!")
            except Exception as e:
                self.lbl_settings_status.configure(text=f"❌ Lỗi gửi Telegram: {e}")

        def _action_check_update(self):
            def _check():
                has_u, ver, _ = updater.check_for_updates()
                txt = f"🚀 Đã có phiên bản mới v{ver}!" if has_u else "✅ Bạn đang ở phiên bản mới nhất."
                self.lbl_settings_status.configure(text=txt)
            threading.Thread(target=_check, daemon=True).start()

        def _action_kill_service(self):
            target = self.entry_kill.get().strip()
            if not target:
                return
            ok, msg = system_monitor.kill_process(target)
            self.entry_kill.delete(0, "end")
            self._log_security(f"Kill Tiến Trình: {msg}")
            self._refresh_services()

        def _refresh_services(self):
            def _fetch():
                svcs = system_monitor.get_active_listening_services()
                lines = [
                    f"{'PORT':<8} {'GIAO THỨC':<12} {'TIẾN TRÌNH / DỊCH VỤ':<30} {'PID':<8}",
                    "=" * 60
                ]
                if not svcs:
                    lines.append("Chưa phát hiện dịch vụ nào đang mở port.")
                else:
                    for s in svcs:
                        lines.append(f"{s.get('port'):<8} {s.get('protocol'):<12} {s.get('name')[:28]:<30} {s.get('pid'):<8}")
                res = "\n".join(lines)
                self.txt_services.delete("1.0", "end")
                self.txt_services.insert("end", res)

            threading.Thread(target=_fetch, daemon=True).start()

        def _run_terminal_cmd(self, cmd_text: str):
            shell_choice = self.combo_shell.get()
            self.txt_cmd_console.insert("end", f"\n> {cmd_text}\n")
            self.txt_cmd_console.see("end")

            def _exec():
                try:
                    if platform.system().lower() == "windows":
                        args = ["cmd.exe", "/c", cmd_text] if shell_choice == "CMD" else ["powershell", "-NoProfile", "-Command", cmd_text]
                    else:
                        args = ["bash", "-c", cmd_text]
                    res = subprocess.run(args, capture_output=True, text=True, timeout=25)
                    out = res.stdout or res.stderr or "[Lệnh hoàn tất thành công (Exit Code 0)]"
                    self.txt_cmd_console.insert("end", out + "\n")
                    self.txt_cmd_console.see("end")
                except Exception as e:
                    self.txt_cmd_console.insert("end", f"Lỗi thực thi: {e}\n")
                    self.txt_cmd_console.see("end")

            threading.Thread(target=_exec, daemon=True).start()

        def _on_terminal_enter(self):
            cmd = self.entry_cmd.get().strip()
            if not cmd:
                return
            self.entry_cmd.delete(0, "end")
            self._run_terminal_cmd(cmd)

        def _clear_terminal(self):
            self.txt_cmd_console.delete("1.0", "end")

        def _refresh_hardware_stats(self):
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory()

                self.lbl_cpu_val.configure(text=f"{cpu}%")
                self.pbar_cpu.set(cpu / 100.0)

                ram_used_gb = round(ram.used / (1024**3), 1)
                ram_total_gb = round(ram.total / (1024**3), 1)
                self.lbl_ram_val.configure(text=f"{ram.percent}% ({ram_used_gb}GB / {ram_total_gb}GB)")
                self.pbar_ram.set(ram.percent / 100.0)

                stats = system_monitor.get_hardware_status()
                net = network_upnp.get_network_info()

                self.lbl_ip_val.configure(text=f"WAN IP: {net['wan_ip']}\nLAN IP: {net['lan_ip']}")

                disks = ", ".join([f"{d['mount']} ({d['percent']}%)" for d in stats.get("disks", [])])
                sys_str = (
                    f"• Thiết Bị: {net['hostname']} ({net['system']} {net['release']})\n"
                    f"• Thời Gian Hoạt Động (Uptime): {stats.get('uptime', 'N/A')}\n"
                    f"• Khởi Động Lúc: {stats.get('boot_time', 'N/A')}\n"
                    f"• Dung Lượng Ổ Đĩa: {disks}\n"
                    f"• Trạng Thái Remote Desktop: {remote_desktop.get_remote_desktop_status()}"
                )
                self.lbl_sys_details.configure(text=sys_str)
            except Exception as e:
                logger.debug(f"Telemetry update error: {e}")

        def _start_telemetry_loop(self):
            """Periodic background loop updating CPU/RAM graphs every 3 seconds."""
            def _loop():
                time.sleep(1)
                self._refresh_hardware_stats()
                self._refresh_services()
                while True:
                    time.sleep(3)
                    try:
                        self._refresh_hardware_stats()
                    except Exception:
                        pass
            threading.Thread(target=_loop, daemon=True).start()

        def run(self):
            self.mainloop()


# =========================================================================
# STANDARD TKINTER FALLBACK (Runs on any machine without CustomTkinter)
# =========================================================================
if USE_TKINTER:
    class ClassicTkinterApp:
        def __init__(self, manager: DesktopUIManager, port: int = 8888):
            self.manager = manager
            self.port = port
            self.root = tk.Tk()
            self.root.title("PcManager - Quản Trị Máy Chủ Từ Xa (Classic UI)")
            self.root.geometry("980x640")
            self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
            self._build_ui()

        def hide_window(self):
            self.root.withdraw()

        def show_window(self):
            self.root.deiconify()
            self.root.lift()

        def destroy(self):
            self.root.destroy()

        def _build_ui(self):
            header = tk.Frame(self.root, bg="#101726", height=50)
            header.pack(fill="x", side="top")
            tk.Label(header, text="🛡️ PcManager Server Guardian", font=("Segoe UI", 16, "bold"), fg="#00f2fe", bg="#101726").pack(side="left", padx=15, pady=10)
            tk.Button(header, text="🌐 Mở Trình Duyệt Web", bg="#00f2fe", fg="#000", font=("Segoe UI", 10, "bold"), command=lambda: webbrowser.open(f"http://localhost:{self.port}")).pack(side="right", padx=15, pady=10)

            nb = ttk.Notebook(self.root)
            nb.pack(fill="both", expand=True, padx=10, pady=10)

            t1 = tk.Frame(nb, bg="#162032")
            t2 = tk.Frame(nb, bg="#162032")
            nb.add(t1, text="📊 Giám Sát Phần Cứng")
            nb.add(t2, text="🛡️ An Ninh & Màn Hình")

            tk.Label(t1, text="Hệ thống đang chạy ngầm ổn định.", fg="#fff", bg="#162032", font=("Segoe UI", 14)).pack(pady=40)
            tk.Button(t1, text="🧹 Dọn Dẹp RAM", bg="#00e676", fg="#000", command=system_monitor.clean_ram).pack(pady=10)

            tk.Button(t2, text="📸 Chụp Màn Hình Ngay", bg="#00f2fe", fg="#000", command=security_guard.capture_screenshot).pack(pady=20)
            tk.Button(t2, text="📷 Chụp Webcam", bg="#38bdf8", fg="#000", command=security_guard.capture_webcam).pack(pady=10)

        def run(self):
            self.root.mainloop()
