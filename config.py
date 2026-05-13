import os
from dotenv import load_dotenv

load_dotenv()


def getenv_str(key: str, default: str = "") -> str:
    value = os.getenv(key, default)
    return value.strip() if isinstance(value, str) else default

BOT_TOKEN = getenv_str("BOT_TOKEN")
BOT_OWNER_ID = int(getenv_str("BOT_OWNER_ID", "0") or "0")
DB_PATH = getenv_str("DB_PATH") or "securebot.db"

# Web server configuration
WEB_HOST = getenv_str("WEB_HOST") or "0.0.0.0"
WEB_PORT = int(getenv_str("WEB_PORT", "8080") or "8080")
WEB_APP_URL = getenv_str("WEB_APP_URL") or "https://swooned-refocus-varmint.ngrok-free.dev"

# Google Safe Browsing API
GOOGLE_SAFE_BROWSING_API_KEY = getenv_str("GOOGLE_SAFE_BROWSING_API_KEY")

DEFAULT_SETTINGS = {
    "enabled": 1,
    "delete_high": 1,
    "warn_medium": 1,
    "reply_low": 0,
    "scan_links": 1,
    "scan_apk": 1,
    "log_channel": None,
    "mute_high_risk": 0,
    "ban_high_risk": 0,
}