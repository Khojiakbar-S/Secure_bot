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
            log_channel TEXT DEFAULT NULL,
            mute_high_risk INTEGER DEFAULT 0,
            ban_high_risk INTEGER DEFAULT 0
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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scanned_urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            score INTEGER NOT NULL,
            level TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
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
                reply_low, scan_links, scan_apk, log_channel,
                mute_high_risk, ban_high_risk
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chat_id,
            DEFAULT_SETTINGS["enabled"],
            DEFAULT_SETTINGS["delete_high"],
            DEFAULT_SETTINGS["warn_medium"],
            DEFAULT_SETTINGS["reply_low"],
            DEFAULT_SETTINGS["scan_links"],
            DEFAULT_SETTINGS["scan_apk"],
            DEFAULT_SETTINGS["log_channel"],
            DEFAULT_SETTINGS["mute_high_risk"],
            DEFAULT_SETTINGS["ban_high_risk"],
        ))
        conn.commit()
    else:
        cur.execute("PRAGMA table_info(chat_settings)")
        existing_columns = {row[1] for row in cur.fetchall()}
        for key, default_value in DEFAULT_SETTINGS.items():
            if key not in existing_columns:
                sql_type = "TEXT" if key == "log_channel" else "INTEGER"
                default_clause = "DEFAULT NULL" if default_value is None else f"DEFAULT {default_value}"
                cur.execute(f"ALTER TABLE chat_settings ADD COLUMN {key} {sql_type} {default_clause}")
        conn.commit()

    conn.close()


def get_settings(chat_id: int) -> dict:
    ensure_chat_settings(chat_id)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()

    settings = dict(row)
    for key, default_value in DEFAULT_SETTINGS.items():
        settings.setdefault(key, default_value)
    return settings


def update_setting(chat_id: int, key: str, value):
    allowed_keys = {
        "enabled",
        "delete_high",
        "warn_medium",
        "reply_low",
        "scan_links",
        "scan_apk",
        "log_channel",
        "mute_high_risk",
        "ban_high_risk",
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


def list_group_chat_ids() -> list[int]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT chat_id FROM chat_settings")
    rows = cur.fetchall()
    conn.close()
    return [row["chat_id"] for row in rows]


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


# URL Cache Functions

def get_cached_url(url: str) -> Optional[dict]:
    """Get cached scan result for a URL."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT url, score, level, timestamp FROM scanned_urls WHERE url = ?",
        (url,)
    )
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "url": row["url"],
            "score": row["score"],
            "level": row["level"],
            "timestamp": row["timestamp"],
        }
    return None


def cache_url_result(url: str, score: int, level: str) -> bool:
    """Cache a URL scan result."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO scanned_urls (url, score, level)
            VALUES (?, ?, ?)
            """,
            (url, score, level)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # URL already cached, update if needed
        return False
    finally:
        conn.close()


def clear_old_cache(days: int = 30) -> int:
    """Clear cache entries older than specified days."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM scanned_urls 
        WHERE timestamp < datetime('now', '-' || ? || ' days')
        """,
        (days,)
    )
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


def get_statistics(chat_id: int = None) -> dict:
    """Get statistics for dashboard."""
    conn = get_connection()
    cur = conn.cursor()

    # Get total scanned URLs
    cur.execute("SELECT COUNT(*) as count FROM scanned_urls")
    links_scanned = cur.fetchone()["count"]

    # Get threats blocked (high risk URLs)
    cur.execute("SELECT COUNT(*) as count FROM scanned_urls WHERE level = 'HIGH'")
    threats_blocked = cur.fetchone()["count"]

    # Get groups protected (unique chat_ids in settings)
    cur.execute("SELECT COUNT(*) as count FROM chat_settings")
    groups_protected = cur.fetchone()["count"]

    # Get APK scans (we'll need to add this table later, for now return 0)
    apks_scanned = 0  # Placeholder

    conn.close()

    return {
        "links_scanned": links_scanned,
        "threats_blocked": threats_blocked,
        "groups_protected": groups_protected,
        "apks_scanned": apks_scanned,
    }