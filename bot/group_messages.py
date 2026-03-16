from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from bot.database import get_settings, is_whitelisted
from bot.link_scanner import scan_links_in_text
from bot.moderation import safe_reply_html, safe_delete_message, send_log_message
from bot.texts import (
    format_link_warning_for_group,
    format_link_reply_low,
    format_log_text,
)


def get_full_name(user) -> str:
    full_name = user.full_name.strip() if user.full_name else "Noma’lum foydalanuvchi"
    return full_name


async def notify_chat_after_delete(update: Update, text: str):
    try:
        await update.effective_chat.send_message(
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except TelegramError:
        pass


async def handle_group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    if not message or not chat or not user:
        return

    settings = get_settings(chat.id)

    document = message.document

    if document and settings["scan_apk"]:

        file_name = document.file_name or ""

        if file_name.lower().endswith(".apk"):

            file = await document.get_file()

            path = f"/tmp/{document.file_unique_id}.apk"

            await file.download_to_drive(path)

            from bot.apk_scanner import scan_apk_file

            result = scan_apk_file(path)

            await message.reply_text(str(result))
  
    if chat.type == "private":
        return

    settings = get_settings(chat.id)

    if not settings["enabled"]:
        return

    if is_whitelisted(chat.id, user.id):
        return

    text = message.text or message.caption or ""

    if settings["scan_links"]:
        link_result = scan_links_in_text(text)
        if link_result:
            await process_link_result(update, context, settings, link_result)


async def process_link_result(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    settings: dict,
    result: dict,
):
    chat = update.effective_chat
    user = update.effective_user
    full_name = get_full_name(user)
    log_chat_id = settings.get("log_channel")

    action = "faqat tekshirildi"

    if result["level"] == "HIGH" and settings["delete_high"]:
        deleted = await safe_delete_message(update)

        if deleted:
            await notify_chat_after_delete(
                update,
                (
                    f"🗑 <b>Xabar o‘chirildi</b>\n\n"
                    f"Foydalanuvchi: <b>{full_name}</b>\n"
                    f"Sabab: shubhali havola\n"
                    f"Daraja: <b>{result['level']}</b>\n"
                    f"Ball: <b>{result['score']}</b>"
                )
            )
            action = "xabar o‘chirildi"
        else:
            await safe_reply_html(update, format_link_warning_for_group(result, full_name))
            action = "o‘chirish urinish bo‘ldi, lekin muvaffaqiyatsiz"

    elif result["level"] == "MEDIUM" and settings["warn_medium"]:
        await safe_reply_html(update, format_link_warning_for_group(result, full_name))
        action = "ogohlantirish yuborildi"

    elif result["level"] == "LOW" and settings["reply_low"]:
        await safe_reply_html(update, format_link_reply_low(result))
        action = "past xavf javobi yuborildi"

    log_text = format_log_text(
        chat_title=chat.title or "Noma’lum guruh",
        user_id=user.id,
        full_name=full_name,
        result=result,
        action=action,
    )
    await send_log_message(context, log_chat_id, log_text)

