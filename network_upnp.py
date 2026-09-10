"""
VNServerSentinel - Network & UPnP Port Manager
Handles dynamic IP tracking, router UPnP port forwarding, and Windows Firewall sync.
No 3rd party middleman tunnels required.
"""

import socket
import logging
import subprocess
import platform
import urllib.request
import json
from typing import Optional, Dict, Any, List

logger = logging.getLogger("VNServerSentinel.Network")

WAN_IP_MIRRORS = [
    "https://api.ipify.org?format=json",
    "https://icanhazip.com",
    "https://ifconfig.me/ip",
    "https://checkip.amazonaws.com",
    "https://api.my-ip.io/v2/ip.json"
]

def get_public_ip() -> Optional[str]:
    """Retrieve public WAN IP via multiple fallback endpoints."""
    for url in WAN_IP_MIRRORS:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                content = response.read().decode("utf-8").strip()
                if content.startswith("{"):
                    try:
                        data = json.loads(content)
                        ip = data.get("ip") or data.get("address")
                        if ip:
                            return ip.strip()
                    except Exception:
                        pass
                else:
                    ip = content.split()[0].strip()
                    if ip and len(ip) <= 45: # IPv4 or IPv6 format
                        return ip
        except Exception as e:
            logger.debug(f"Failed to fetch WAN IP from {url}: {e}")
            continue
    return None

def get_local_ip() -> str:
    """Retrieve local LAN IPv4 address of the active network interface."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually send data over the wire
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"
    finally:
        s.close()
    return local_ip

def get_network_info() -> Dict[str, Any]:
    """Get comprehensive network status for the server."""
    wan_ip = get_public_ip() or "Không xác định"
    lan_ip = get_local_ip()
    hostname = socket.gethostname()
    return {
        "hostname": hostname,
        "wan_ip": wan_ip,
        "lan_ip": lan_ip,
        "system": platform.system(),
        "release": platform.release(),
    }

class UPnPManager:
    """Manages router port forwarding dynamically via UPnP/IGD protocol."""

    def __init__(self):
        self.device = None
        self.local_ip = get_local_ip()
        self._init_upnp()

    def _init_upnp(self):
        """Try initializing UPnP via upnpy library."""
        try:
            import upnpy
            upnp = upnpy.UPnP()
            logger.info("Discovering UPnP devices on local network...")
            upnp.discover(delay=2)
            self.device = upnp.get_igd()
            logger.info(f"UPnP IGD Device discovered: {self.device}")
        except Exception as e:
            logger.warning(f"UPnP initialization notice: {e}. Falling back to manual SSDP/UPnP.")
            self.device = None

    def open_port(self, external_port: int, internal_port: int, protocol: str = "TCP", description: str = "VNServerSentinel") -> tuple[bool, str]:
        """
        Request the router to forward external_port to this machine's internal_port.
        Also synchronizes Windows Defender Firewall.
        """
        protocol = protocol.upper()
        if protocol not in ("TCP", "UDP"):
            return False, "Giao thức không hợp lệ. Chỉ hỗ trợ TCP hoặc UDP."

        self.local_ip = get_local_ip()
        success = False
        message = ""

        # 1. Try via upnpy if available
        if self.device:
            try:
                # Add port mapping via upnpy
                self.device.add_port_mapping(
                    external_port=int(external_port),
                    internal_port=int(internal_port),
                    protocol=protocol,
                    internal_client=self.local_ip,
                    description=description
                )
                success = True
                message = f"Đã mở port {external_port} ➔ {self.local_ip}:{internal_port} ({protocol}) qua UPnP."
            except Exception as e:
                logger.error(f"upnpy open_port error: {e}")
                message = f"Lỗi UPnP router: {e}"

        # 2. If upnpy failed or not present, try miniupnpc or SOAP fallback
        if not success:
            success, msg = self._fallback_open_port(external_port, internal_port, protocol, description)
            if success:
                message = msg
            else:
                message = f"Không thể ra lệnh cho router qua UPnP: {msg} (Hãy đảm bảo Router Wi-Fi đã bật tính năng UPnP)"

        # 3. Synchronize Windows Firewall regardless
        fw_status = self.sync_windows_firewall(internal_port, protocol, allow=True)
        if fw_status:
            message += "\n🧱 Đã tự động tạo luật cho phép trên Windows Firewall."
        else:
            message += "\n⚠️ Không thể cấu hình Windows Firewall (Cần chạy với quyền Administrator)."

        return success, message

    def close_port(self, external_port: int, protocol: str = "TCP") -> tuple[bool, str]:
        """Remove port mapping on the router and close Windows Firewall."""
        protocol = protocol.upper()
        success = False
        message = ""

        if self.device:
            try:
                self.device.delete_port_mapping(external_port=int(external_port), protocol=protocol)
                success = True
                message = f"Đã xóa ánh xạ port {external_port} ({protocol}) trên Router."
            except Exception as e:
                message = f"Lỗi đóng port UPnP: {e}"

        if not success:
            success, msg = self._fallback_close_port(external_port, protocol)
            if success:
                message = msg

        # Delete Windows Firewall Rule
        self.sync_windows_firewall(external_port, protocol, allow=False)
        return success, message

    def _fallback_open_port(self, external_port: int, internal_port: int, protocol: str, description: str) -> tuple[bool, str]:
        """Try miniupnpc wrapper if available."""
        try:
            import miniupnpc
            u = miniupnpc.UPnP()
            u.discoverdelay = 200
            u.discover()
            u.selectigd()
            u.addportmapping(int(external_port), protocol, self.local_ip, int(internal_port), description, '')
            return True, f"Đã mở port {external_port} ➔ {self.local_ip}:{internal_port} qua miniupnpc."
        except Exception as e:
            return False, str(e)

    def _fallback_close_port(self, external_port: int, protocol: str) -> tuple[bool, str]:
        """Try miniupnpc wrapper to delete port."""
        try:
            import miniupnpc
            u = miniupnpc.UPnP()
            u.discoverdelay = 200
            u.discover()
            u.selectigd()
            u.deleteportmapping(int(external_port), protocol)
            return True, f"Đã đóng port {external_port} qua miniupnpc."
        except Exception as e:
            return False, str(e)

    def list_ports(self) -> List[Dict[str, Any]]:
        """List active port mappings from router if supported."""
        mappings = []
        try:
            if self.device and hasattr(self.device, "get_port_mappings"):
                return self.device.get_port_mappings()
        except Exception as e:
            logger.debug(f"Unable to query port mappings: {e}")
        return mappings

    @staticmethod
    def sync_windows_firewall(port: int, protocol: str = "TCP", allow: bool = True) -> bool:
        """Add or remove an inbound rule in Windows Defender Firewall via netsh."""
        if platform.system().lower() != "windows":
            logger.info(f"[Mock FW] Non-windows system: port {port}/{protocol} allow={allow}")
            return True

        rule_name = f"VNServerSentinel_{protocol}_{port}"
        try:
            # First, clean existing rule with this name if exists
            subprocess.run(
                f'netsh advfirewall firewall delete rule name="{rule_name}"',
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            if allow:
                cmd = f'netsh advfirewall firewall add rule name="{rule_name}" dir=in action=allow protocol={protocol} localport={port}'
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return res.returncode == 0
            return True
        except Exception as e:
            logger.error(f"Firewall sync error: {e}")
            return False
