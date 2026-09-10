"""
VNServerSentinel - Configuration Management
Loads settings from .env file or environment variables.
"""

import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

def load_dotenv_fallback():
    """Fallback .env parser if python-dotenv is not yet installed."""
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    load_dotenv_fallback()

class Config:
    BASE_DIR: Path = BASE_DIR

    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    TELEGRAM_ADMIN_CHAT_ID: str = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "").strip()
    ADMIN_PIN: str = os.getenv("ADMIN_PIN", "1234").strip()

    # Cloud Heartbeat (Healthchecks.io / Uptime Kuma push)
    HEARTBEAT_URL: str = os.getenv("HEARTBEAT_URL", "").strip()

    # GitHub repository for Safe Auto-Update (owner/repo)
    GITHUB_REPO: str = os.getenv("GITHUB_REPO", "owner/VNServerSentinel").strip()
    AUTO_UPDATE_ENABLED: bool = os.getenv("AUTO_UPDATE_ENABLED", "true").lower() in ("true", "1", "yes")

    # Intervals & Security
    CHECK_INTERVAL_SECONDS: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))
    ENABLE_WEBCAM: bool = os.getenv("ENABLE_WEBCAM", "true").lower() in ("true", "1", "yes")
    ENABLE_INTRUDER_ALERT: bool = os.getenv("ENABLE_INTRUDER_ALERT", "true").lower() in ("true", "1", "yes")

    # Storage paths
    DATA_DIR: Path = BASE_DIR / "data"
    SNAPSHOT_DIR: Path = DATA_DIR / "snapshots"
    BACKUP_DIR: Path = DATA_DIR / "backup"
    STAGING_DIR: Path = DATA_DIR / "staging"

    @classmethod
    def ensure_directories(cls):
        """Ensure all required runtime directories exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        cls.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        cls.STAGING_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls) -> tuple[bool, str]:
        """Validate critical configuration parameters."""
        if not cls.TELEGRAM_BOT_TOKEN or cls.TELEGRAM_BOT_TOKEN.startswith("123456789:"):
            return False, "TELEGRAM_BOT_TOKEN chưa được cấu hình chính xác trong file .env!"
        if not cls.TELEGRAM_ADMIN_CHAT_ID or cls.TELEGRAM_ADMIN_CHAT_ID == "987654321":
            return False, "TELEGRAM_ADMIN_CHAT_ID chưa được cấu hình trong file .env!"
        return True, "Config hợp lệ."
