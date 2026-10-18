"""
VNServerSentinel - System & Power Outage Monitor
Tracks hardware performance (CPU, RAM, Disks, Uptime),
detects unexpected power cuts/crashes, and calculates downtime.
"""

import os
import json
import time
import logging
import platform
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import psutil
from config import Config

logger = logging.getLogger("VNServerSentinel.System")

STATE_FILE = Config.DATA_DIR / "state.json"

def get_system_uptime_seconds() -> float:
    """Return system uptime in seconds."""
    return time.time() - psutil.boot_time()

def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    d = int(seconds // 86400)
    h = int((seconds % 86400) // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    parts = []
    if d > 0:
        parts.append(f"{d} ngày")
    if h > 0 or d > 0:
        parts.append(f"{h} giờ")
    parts.append(f"{m} phút")
    parts.append(f"{s} giây")
    return " ".join(parts)

def get_hardware_status() -> Dict[str, Any]:
    """Collect comprehensive hardware statistics."""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count(logical=True)
    
    mem = psutil.virtual_memory()
    ram_total_gb = round(mem.total / (1024**3), 2)
    ram_used_gb = round(mem.used / (1024**3), 2)
    ram_percent = mem.percent

    disks = []
    for part in psutil.disk_partitions(all=False):
        # Filter read-only or CD-ROMs
        if "cdrom" in part.opts or not part.fstype:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "mount": part.mountpoint,
                "total_gb": round(usage.total / (1024**3), 1),
                "free_gb": round(usage.free / (1024**3), 1),
                "percent": usage.percent
            })
        except Exception:
            continue

    active_users = []
    for u in psutil.users():
        active_users.append({
            "name": u.name,
            "terminal": u.terminal or "Console",
            "host": u.host or "Local",
            "started": datetime.fromtimestamp(u.started).strftime("%H:%M:%S")
        })

    boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    uptime = format_duration(get_system_uptime_seconds())

    return {
        "cpu_percent": cpu_percent,
        "cpu_count": cpu_count,
        "ram_total_gb": ram_total_gb,
        "ram_used_gb": ram_used_gb,
        "ram_percent": ram_percent,
        "disks": disks,
        "active_users": active_users,
        "boot_time": boot_time,
        "uptime": uptime
    }

def check_power_cut_history() -> Optional[Dict[str, Any]]:
    """
    Examines previous state to determine if a sudden reboot / power loss occurred.
    Calculates estimated downtime.
    """
    Config.ensure_directories()
    current_boot_time = psutil.boot_time()
    reboot_info = None

    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                prev_state = json.load(f)

            prev_boot_time = prev_state.get("boot_time", 0)
            prev_last_seen = prev_state.get("last_seen", 0)

            # If the boot time is newer than previous boot time, the PC restarted!
            if current_boot_time > (prev_boot_time + 10):
                downtime_sec = max(0, current_boot_time - prev_last_seen)
                
                # Check Windows Event Log for unexpected shutdown reason
                shutdown_reason = check_windows_shutdown_event()

                reboot_info = {
                    "last_seen_str": datetime.fromtimestamp(prev_last_seen).strftime("%Y-%m-%d %H:%M:%S"),
                    "reboot_time_str": datetime.fromtimestamp(current_boot_time).strftime("%Y-%m-%d %H:%M:%S"),
                    "downtime_str": format_duration(downtime_sec),
                    "reason": shutdown_reason
                }
        except Exception as e:
            logger.error(f"Error reading power cut history: {e}")

    # Update state file with current boot time and current timestamp
    update_heartbeat_state()
    return reboot_info

def update_heartbeat_state():
    """Save current timestamp and boot time for future power outage comparisons."""
    try:
        Config.ensure_directories()
        state = {
            "boot_time": psutil.boot_time(),
            "last_seen": time.time(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving heartbeat state: {e}")

def check_windows_shutdown_event() -> str:
    """Inspect Windows Event Log for unexpected power loss (Event ID 41/6008)."""
    if platform.system().lower() != "windows":
        return "Khởi động lại bình thường hoặc không xác định (Môi trường kiểm thử)."

    try:
        # PowerShell query for the most recent unexpected shutdown event
        ps_cmd = (
            "Get-WinEvent -FilterHashtable @{LogName='System'; Id=41,6008} -MaxEvents 1 "
            "| Select-Object -ExpandProperty Message"
        )
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=5
        )
        if res.returncode == 0 and res.stdout.strip():
            msg = res.stdout.strip()
            if "unexpectedly" in msg.lower() or "shut down" in msg.lower() or "power" in msg.lower():
                return "🚨 Sập nguồn đột ngột (Mất điện hoặc tắt nguồn cứng / Kernel-Power Event)"
            return f"Sự kiện ghi nhận: {msg[:100]}"
    except Exception:
        pass
    return "Khởi động lại (Có thể do cúp điện hoặc khởi động lại hệ thống)"

def get_active_listening_services() -> list[dict]:
    """Scan all active TCP/UDP listening ports and identify the services and processes using them."""
    services = []
    seen = set()
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.status == psutil.CONN_LISTEN and c.laddr:
                proto = "TCP" if c.type == 1 else "UDP"
                port = c.laddr.port
                ip = c.laddr.ip
                key = (proto, port)
                if key in seen:
                    continue
                seen.add(key)

                pid = c.pid
                pname = "Hệ thống / Windows Service"
                cmdline = ""
                mem_mb = 0.0
                if pid:
                    try:
                        p = psutil.Process(pid)
                        pname = p.name()
                        cmdline = " ".join(p.cmdline() or [])
                        mem_mb = round(p.memory_info().rss / (1024 * 1024), 1)
                    except Exception:
                        pass

                # Smart recognition for common servers (Minecraft, 9Router, Web, DB, etc.)
                desc = "Ứng dụng mạng"
                lower_cmd = cmdline.lower()
                lower_name = pname.lower()
                if "minecraft" in lower_cmd or "spigot" in lower_cmd or "paper" in lower_cmd or port == 25565:
                    desc = "🎮 Minecraft Server"
                elif "9router" in lower_cmd or "9router" in lower_name:
                    desc = "🌐 9Router Service"
                elif port == 3389:
                    desc = "🖥️ Windows RDP (Remote Desktop)"
                elif port == 8888:
                    desc = "🛡️ PcManager Web Dashboard"
                elif "rustdesk" in lower_name:
                    desc = "⚡ RustDesk Remote Desktop"
                elif "python" in lower_name and "main.py" in lower_cmd:
                    desc = "🛡️ PcManager Core"
                elif "mysql" in lower_name or port == 3306:
                    desc = "🗄️ MySQL Database"
                elif "postgres" in lower_name or port == 5432:
                    desc = "🗄️ PostgreSQL Database"
                elif "redis" in lower_name or port == 6379:
                    desc = "⚡ Redis In-Memory Cache"
                elif "node" in lower_name:
                    desc = "🟢 Node.js Web App"
                elif "nginx" in lower_name or "httpd" in lower_name:
                    desc = "🌍 Nginx/Apache Web Server"
                elif "qbittorrent" in lower_name or (port == 8080 and "qbit" in lower_cmd):
                    desc = "📥 qBittorrent Web UI"
                elif port == 80 or port == 443:
                    desc = "🌐 HTTP/HTTPS Web Server"

                services.append({
                    "protocol": proto,
                    "port": port,
                    "ip": ip,
                    "pid": pid,
                    "process": pname,
                    "desc": desc,
                    "mem_mb": mem_mb,
                    "cmdline": cmdline[:150]
                })
    except Exception as e:
        logger.error(f"Error scanning active listening services: {e}")

    services.sort(key=lambda x: x["port"])
    return services

def get_top_processes(limit: int = 5) -> list[dict]:
    """Retrieve top memory and CPU consuming processes."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "memory_info"]):
        try:
            mem_mb = round(p.info["memory_info"].rss / (1024 * 1024), 1)
            procs.append({
                "pid": p.info["pid"],
                "name": p.info["name"],
                "cpu": p.info["cpu_percent"] or 0.0,
                "mem_mb": mem_mb,
                "mem_percent": round(p.info["memory_percent"] or 0.0, 1)
            })
        except Exception:
            pass
    procs.sort(key=lambda x: x["mem_mb"], reverse=True)
    return procs[:limit]

def clean_ram() -> tuple[bool, str]:
    """Release unneeded working sets and purged standby memory across processes."""
    if platform.system().lower() != "windows":
        try:
            mem = psutil.virtual_memory()
            return True, f"🧹 Đã kiểm tra tài nguyên bộ nhớ: RAM đang dùng {mem.percent}% ({round(mem.used/(1024**3), 2)}GB / {round(mem.total/(1024**3), 2)}GB)."
        except Exception as e:
            return False, f"Lỗi: {e}"

    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi

        before_mem = psutil.virtual_memory()
        PROCESS_SET_QUOTA = 0x0100
        PROCESS_QUERY_INFORMATION = 0x0400

        freed_count = 0
        for p in psutil.process_iter(["pid", "name"]):
            try:
                pid = p.info["pid"]
                if pid <= 4:
                    continue
                handle = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, False, pid)
                if handle:
                    psapi.EmptyWorkingSet(handle)
                    kernel32.CloseHandle(handle)
                    freed_count += 1
            except Exception:
                pass

        after_mem = psutil.virtual_memory()
        freed_mb = round((before_mem.used - after_mem.used) / (1024 * 1024), 1)
        if freed_mb < 0:
            freed_mb = 0.0

        return True, (
            f"🧹 *ĐÃ DỌN DẸP & THU HỒI RAM THÀNH CÔNG!*\n\n"
            f"⚡ Đã tối ưu hóa: `{freed_count}` tiến trình Windows\n"
            f"💾 Giải phóng ước tính: `~{freed_mb} MB RAM`\n"
            f"🧠 RAM hiện tại: `{after_mem.percent}%` ({round(after_mem.used/(1024**3), 2)}GB / {round(after_mem.total/(1024**3), 2)}GB)"
        )
    except Exception as e:
        logger.error(f"Error executing RAM clean: {e}")
        return False, f"Lỗi dọn RAM: {e}"

def kill_process(identifier: Any) -> tuple[bool, str]:
    """Terminate process by PID or executable name."""
    try:
        if str(identifier).isdigit():
            pid = int(identifier)
            p = psutil.Process(pid)
            name = p.name()
            p.terminate()
            return True, f"🛑 Đã gửi lệnh buộc dừng tiến trình `{name}` (PID: `{pid}`)."
        else:
            name_target = str(identifier).lower()
            killed = 0
            for p in psutil.process_iter(["pid", "name"]):
                try:
                    if p.info["name"] and p.info["name"].lower() == name_target:
                        p.terminate()
                        killed += 1
                except Exception:
                    pass
            if killed > 0:
                return True, f"🛑 Đã buộc dừng `{killed}` tiến trình có tên `{identifier}`."
            return False, f"⚠️ Không tìm thấy tiến trình nào có tên `{identifier}` đang chạy."
    except Exception as e:
        logger.error(f"Error terminating process {identifier}: {e}")
        return False, f"Lỗi khi tắt tiến trình: {e}"
