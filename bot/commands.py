import logging
import os
import tempfile
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, FSInputFile
from telegram.constants import ChatType
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from config import WEB_APP_URL, BOT_OWNER_ID, DB_PATH

logger = logging.getLogger(__name__)

from bot.database import (
    get_settings,
    update_setting,
    add_whitelist,
    add_blacklist,
    remove_whitelist,
    list_whitelist,
)
from bot.link_scanner import extract_urls
from bot.texts import (
    START_TEXT,
    HELP_TEXT,
    format_settings_inline,
    setting_updated_text,
    setlog_updated_text,
    whitelist_add_text,
    whitelist_del_text,
    whitelist_list_text,
    NOT_ADMIN_TEXT,
    SETLOG_USAGE_TEXT,
    WHITELIST_USAGE_TEXT,
)


ALLOWED_SETTING_KEYS = {
    "enabled",
    "delete_high",
    "warn_medium",
    "reply_low",
    "scan_links",
    "scan_apk",
    "mute_high_risk",
    "ban_high_risk",
}

# Setting button labels mapping
SETTING_LABELS = {
    "enabled": "🤖 Bot Enabled",
    "delete_high": "🗑️ Delete High Risk",
    "warn_medium": "⚠️ Warn Medium Risk",
    "reply_low": "💬 Reply Low Risk",
    "scan_links": "🔗 Scan Links",
    "scan_apk": "📦 Scan APK",
    "mute_high_risk": "🔇 Mute High Risk",
    "ban_high_risk": "🚫 Ban High Risk",
}


async def is_admin(update: Update, user_id: int) -> bool:
    chat = update.effective_chat
    if chat.type == ChatType.PRIVATE:
        return True

    member = await chat.get_member(user_id)
    return member.status in ("administrator", "creator")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(START_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(HELP_TEXT)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send settings with inline keyboard buttons."""
    chat_id = update.effective_chat.id
    settings = get_settings(chat_id)
    
    # Build inline keyboard
    keyboard = []
    
    # Row 1: Enabled, Delete High Risk
    keyboard.append([
        InlineKeyboardButton(
            text=f"{'✅' if settings['enabled'] else '❌'} {SETTING_LABELS['enabled']}",
            callback_data="toggle_enabled"
        ),
        InlineKeyboardButton(
            text=f"{'✅' if settings['delete_high'] else '❌'} {SETTING_LABELS['delete_high']}",
            callback_data="toggle_delete_high"
        ),
    ])
    
    # Row 2: Warn Medium Risk, Reply Low Risk
    keyboard.append([
        InlineKeyboardButton(
            text=f"{'✅' if settings['warn_medium'] else '❌'} {SETTING_LABELS['warn_medium']}",
            callback_data="toggle_warn_medium"
        ),
        InlineKeyboardButton(
            text=f"{'✅' if settings['reply_low'] else '❌'} {SETTING_LABELS['reply_low']}",
            callback_data="toggle_reply_low"
        ),
    ])
    
    # Row 3: Scan Links, Scan APK
    keyboard.append([
        InlineKeyboardButton(
            text=f"{'✅' if settings['scan_links'] else '❌'} {SETTING_LABELS['scan_links']}",
            callback_data="toggle_scan_links"
        ),
        InlineKeyboardButton(
            text=f"{'✅' if settings['scan_apk'] else '❌'} {SETTING_LABELS['scan_apk']}",
            callback_data="toggle_scan_apk"
        ),
    ])
    
    # Row 4: Mute High Risk, Ban High Risk
    keyboard.append([
        InlineKeyboardButton(
            text=f"{'✅' if settings['mute_high_risk'] else '❌'} {SETTING_LABELS['mute_high_risk']}",
            callback_data="toggle_mute_high_risk"
        ),
        InlineKeyboardButton(
            text=f"{'✅' if settings['ban_high_risk'] else '❌'} {SETTING_LABELS['ban_high_risk']}",
            callback_data="toggle_ban_high_risk"
        ),
    ])
    
    # Row 5: Set Log Channel
    keyboard.append([
        InlineKeyboardButton(
            text="📋 Set Log Channel",
            callback_data="set_log_channel"
        ),
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(
        format_settings_inline(settings),
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )


async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send dashboard with Web App button."""
    chat = update.effective_chat

    if chat.type != ChatType.PRIVATE:
        bot_username = context.bot.username or os.getenv("BOT_USERNAME", "your_bot")
        deeplink = f"https://t.me/{bot_username}?start=dashboard"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(text="Open in private chat", url=deeplink)]
        ])

        await update.message.reply_text(
            "Please message me in private to access the dashboard.",
            reply_markup=reply_markup
        )
        return

    if not WEB_APP_URL or not WEB_APP_URL.startswith("https://"):
        await update.message.reply_text(
            "❌ The dashboard URL is not configured correctly. "
            "Please set WEB_APP_URL to a valid HTTPS URL in .env."
        )
        return

    keyboard = [
        [InlineKeyboardButton(
            text="📊 Open Dashboard",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await update.message.reply_html(
            "<b>🔒 SecureBot Dashboard</b>\n\n"
            "Click the button below to open the modern web dashboard where you can manage all bot settings and view statistics.",
            reply_markup=reply_markup
        )
    except BadRequest as error:
        if "Button_type_invalid" in str(error):
            logger.exception("Web App button failed with Button_type_invalid")
            await update.message.reply_text(
                "❌ Unable to open dashboard with Web App at this time."
            )
        else:
            raise


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks."""
    query = update.callback_query
    user_id = update.effective_user.id
    chat_id = query.message.chat_id
    
    # Check if user is admin
    if not await is_admin(update, user_id):
        await query.answer(NOT_ADMIN_TEXT, show_alert=True)
        return
    
    callback_data = query.data
    settings = get_settings(chat_id)
    
    # Handle toggle buttons
    if callback_data.startswith("toggle_"):
        setting_key = callback_data.replace("toggle_", "")
        
        if setting_key not in ALLOWED_SETTING_KEYS:
            await query.answer("Invalid setting", show_alert=True)
            return
        
        # Toggle the setting
        new_value = 1 - settings[setting_key]
        update_setting(chat_id, setting_key, new_value)
        
        # Acknowledge the button press
        await query.answer(f"✅ Setting updated!")
        
        # Refresh the settings message
        settings = get_settings(chat_id)
        keyboard = build_settings_keyboard(settings)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=format_settings_inline(settings),
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    
    elif callback_data == "set_log_channel":
        # Store the state for next message
        context.user_data["waiting_for_log_channel"] = True
        await query.answer()
        await query.edit_message_text(
            text="📋 <b>Set Log Channel</b>\n\nPlease reply with the chat ID or forward a message from the channel where you want logs to be sent.\n\n"
                 f"Current log channel: <code>{settings.get('log_channel') or 'not set'}</code>",
            parse_mode="HTML",
        )


def build_settings_keyboard(settings: dict) -> list:
    """Build the inline keyboard for settings."""
    keyboard = []
    
    # Row 1: Enabled, Delete High Risk
    keyboard.append([
        InlineKeyboardButton(
            text=f"{'✅' if settings['enabled'] else '❌'} {SETTING_LABELS['enabled']}",
            callback_data="toggle_enabled"
        ),
        InlineKeyboardButton(
            text=f"{'✅' if settings['delete_high'] else '❌'} {SETTING_LABELS['delete_high']}",
            callback_data="toggle_delete_high"
        ),
    ])
    
    # Row 2: Warn Medium Risk, Reply Low Risk
    keyboard.append([
        InlineKeyboardButton(
            text=f"{'✅' if settings['warn_medium'] else '❌'} {SETTING_LABELS['warn_medium']}",
            callback_data="toggle_warn_medium"
        ),
        InlineKeyboardButton(
            text=f"{'✅' if settings['reply_low'] else '❌'} {SETTING_LABELS['reply_low']}",
            callback_data="toggle_reply_low"
        ),
    ])
    
    # Row 3: Scan Links, Scan APK
    keyboard.append([
        InlineKeyboardButton(
            text=f"{'✅' if settings['scan_links'] else '❌'} {SETTING_LABELS['scan_links']}",
            callback_data="toggle_scan_links"
        ),
        InlineKeyboardButton(
            text=f"{'✅' if settings['scan_apk'] else '❌'} {SETTING_LABELS['scan_apk']}",
            callback_data="toggle_scan_apk"
        ),
    ])
    
    # Row 4: Mute High Risk, Ban High Risk
    keyboard.append([
        InlineKeyboardButton(
            text=f"{'✅' if settings['mute_high_risk'] else '❌'} {SETTING_LABELS['mute_high_risk']}",
            callback_data="toggle_mute_high_risk"
        ),
        InlineKeyboardButton(
            text=f"{'✅' if settings['ban_high_risk'] else '❌'} {SETTING_LABELS['ban_high_risk']}",
            callback_data="toggle_ban_high_risk"
        ),
    ])
    
    # Row 5: Set Log Channel
    keyboard.append([
        InlineKeyboardButton(
            text="📋 Set Log Channel",
            callback_data="set_log_channel"
        ),
    ])
    
    return keyboard


async def setlog_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setlog command - legacy for compatibility."""
    user_id = update.effective_user.id

    if not await is_admin(update, user_id):
        await update.message.reply_text(NOT_ADMIN_TEXT)
        return

    args = context.args
    if len(args) != 1:
        await update.message.reply_html(SETLOG_USAGE_TEXT)
        return

    log_chat_id = args[0].strip()
    chat_id = update.effective_chat.id

    update_setting(chat_id, "log_channel", log_chat_id)
    await update.message.reply_html(setlog_updated_text(log_chat_id))


async def whitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_admin(update, user_id):
        await update.message.reply_text(NOT_ADMIN_TEXT)
        return

    args = context.args
    if not args:
        await update.message.reply_html(WHITELIST_USAGE_TEXT)
        return

    action = args[0].lower().strip()
    chat_id = update.effective_chat.id

    if action == "list":
        users = list_whitelist(chat_id)
        await update.message.reply_html(whitelist_list_text(users))
        return

    if action not in ("add", "del") or len(args) != 2:
        await update.message.reply_html(WHITELIST_USAGE_TEXT)
        return

    try:
        target_user_id = int(args[1])
    except ValueError:
        await update.message.reply_html(WHITELIST_USAGE_TEXT)
        return

    if action == "add":
        added = add_whitelist(chat_id, target_user_id)
        await update.message.reply_html(whitelist_add_text(target_user_id, added))
    else:
        removed = remove_whitelist(chat_id, target_user_id)
        await update.message.reply_html(whitelist_del_text(target_user_id, removed))


async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID:
        await update.message.reply_text(NOT_ADMIN_TEXT)
        return

    db_path = Path(DB_PATH)
    if not db_path.exists():
        await update.message.reply_text("Database file not found.")
        return

    try:
        db_input = FSInputFile(str(db_path))
        await context.bot.send_document(
            chat_id=BOT_OWNER_ID,
            document=db_input,
            filename=db_path.name,
            caption="SecureBot database backup"
        )
        await update.message.reply_text("Database backup sent to the admin.")
    except Exception as exc:
        logging.exception("Failed to send database backup")
        await update.message.reply_text("Failed to create or send the backup.")


async def restore_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID:
        return

    message = update.effective_message
    if not message or not message.document:
        return

    caption = (message.caption or "").strip().lower()
    if not caption.startswith("/restore"):
        return

    document = message.document
    temp_file = Path(tempfile.gettempdir()) / f"securebot_restore_{document.file_unique_id}.db"
    db_path = Path(DB_PATH)

    try:
        file = await document.get_file()
        await file.download_to_drive(str(temp_file))
        os.replace(str(temp_file), str(db_path))
        await message.reply_text("Database successfully restored! ✅")
    except Exception:
        logging.exception("Failed to restore database from uploaded file")
        await message.reply_text("Failed to restore database. Please try again.")
    finally:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass


async def blacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_admin(update, user_id):
        await update.message.reply_text(NOT_ADMIN_TEXT)
        return

    message = update.message
    if not message or not message.reply_to_message:
        await update.message.reply_text(
            "Please reply to the message containing the link and use /blacklist."
        )
        return

    source_message = message.reply_to_message
    text = source_message.text or source_message.caption or ""
    urls = extract_urls(text)

    if not urls:
        await update.message.reply_text(
            "No link found in the replied message. Please reply to a message that contains a URL."
        )
        return

    url_to_blacklist = urls[0].strip()
    added = add_blacklist(update.effective_chat.id, url_to_blacklist)

    try:
        await source_message.delete()
    except Exception:
        pass

    if added:
        await update.message.reply_text("✅ Link added to blacklist!")
    else:
        await update.message.reply_text("ℹ️ This link is already on the blacklist.")
