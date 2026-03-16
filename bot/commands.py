from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ContextTypes

from bot.database import (
    get_settings,
    update_setting,
    add_whitelist,
    remove_whitelist,
    list_whitelist,
)
from bot.texts import (
    START_TEXT,
    HELP_TEXT,
    format_settings,
    setting_updated_text,
    setlog_updated_text,
    whitelist_add_text,
    whitelist_del_text,
    whitelist_list_text,
    NOT_ADMIN_TEXT,
    UNKNOWN_SETTING_TEXT,
    SET_USAGE_TEXT,
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
    chat_id = update.effective_chat.id
    settings = get_settings(chat_id)
    await update.message.reply_html(format_settings(settings))


async def set_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_admin(update, user_id):
        await update.message.reply_text(NOT_ADMIN_TEXT)
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_html(SET_USAGE_TEXT)
        return

    key = args[0].strip()
    value = args[1].strip().lower()

    if key not in ALLOWED_SETTING_KEYS:
        await update.message.reply_text(UNKNOWN_SETTING_TEXT)
        return

    if value not in ("on", "off"):
        await update.message.reply_html(SET_USAGE_TEXT)
        return

    bool_value = 1 if value == "on" else 0
    chat_id = update.effective_chat.id

    update_setting(chat_id, key, bool_value)
    await update.message.reply_html(setting_updated_text(key, bool(bool_value)))


async def setlog_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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