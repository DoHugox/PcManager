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
