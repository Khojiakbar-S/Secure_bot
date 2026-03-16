import sqlite3
from typing import Optional
from config import DB_PATH, DEFAULT_SETTINGS


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_settings (
            chat_id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            delete_high INTEGER DEFAULT 1,
            warn_medium INTEGER DEFAULT 1,
            reply_low INTEGER DEFAULT 0,
            scan_links INTEGER DEFAULT 1,
            scan_apk INTEGER DEFAULT 1,
            log_channel TEXT DEFAULT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            UNIQUE(chat_id, user_id)
        )
    """)

    conn.commit()
    conn.close()


def ensure_chat_settings(chat_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT chat_id FROM chat_settings WHERE chat_id = ?", (chat_id,))
    exists = cur.fetchone()

    if not exists:
        cur.execute("""
            INSERT INTO chat_settings (
                chat_id, enabled, delete_high, warn_medium,
                reply_low, scan_links, scan_apk, log_channel
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chat_id,
            DEFAULT_SETTINGS["enabled"],
            DEFAULT_SETTINGS["delete_high"],
            DEFAULT_SETTINGS["warn_medium"],
            DEFAULT_SETTINGS["reply_low"],
            DEFAULT_SETTINGS["scan_links"],
            DEFAULT_SETTINGS["scan_apk"],
            DEFAULT_SETTINGS["log_channel"],
        ))
        conn.commit()

    conn.close()


def get_settings(chat_id: int) -> dict:
    ensure_chat_settings(chat_id)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()

    return dict(row)


def update_setting(chat_id: int, key: str, value):
    allowed_keys = {
        "enabled",
        "delete_high",
        "warn_medium",
        "reply_low",
        "scan_links",
        "scan_apk",
        "log_channel",
    }

    if key not in allowed_keys:
        raise ValueError("Noto'g'ri sozlama kaliti.")

    ensure_chat_settings(chat_id)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE chat_settings SET {key} = ? WHERE chat_id = ?", (value, chat_id))
    conn.commit()
    conn.close()


def add_whitelist(chat_id: int, user_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO whitelist (chat_id, user_id) VALUES (?, ?)",
            (chat_id, user_id)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def remove_whitelist(chat_id: int, user_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM whitelist WHERE chat_id = ? AND user_id = ?",
        (chat_id, user_id)
    )
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def list_whitelist(chat_id: int) -> list[int]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM whitelist WHERE chat_id = ? ORDER BY user_id", (chat_id,))
    rows = cur.fetchall()
    conn.close()
    return [row["user_id"] for row in rows]


def is_whitelisted(chat_id: int, user_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM whitelist WHERE chat_id = ? AND user_id = ?",
        (chat_id, user_id)
    )
    result = cur.fetchone() is not None
    conn.close()
    return result