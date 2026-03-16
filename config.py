import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "securebot.db")

DEFAULT_SETTINGS = {
    "enabled": 1,
    "delete_high": 1,
    "warn_medium": 1,
    "reply_low": 0,
    "scan_links": 1,
    "scan_apk": 1,
    "log_channel": None,
}