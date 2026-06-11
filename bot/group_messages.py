import tempfile
import os
from pathlib import Path
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes
from bot.virustotal import check_file_hash_virustotal 

from bot.database import get_settings, is_whitelisted, is_blacklisted_url
from bot.link_scanner import extract_urls, scan_links_in_text
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

            # Vaqtinchalik fayl yaratish
            temp_dir = tempfile.gettempdir()
            path = os.path.join(temp_dir, f"{document.file_unique_id}.apk")
            await file.download_to_drive(path)

            try:
                from bot.apk_scanner import scan_apk_file

                # 1. Ichki evristik tekshiruv (Permissions va DEX)
                local_result = scan_apk_file(path)
                
                # 2. Global VirusTotal tekshiruvi (Antiviruslar bazasi)
                vt_result = await check_file_hash_virustotal(path)
                
                is_virus = False
                reasons = list(local_result.get("reasons", []))
                score = local_result.get("score", 0)

                if vt_result:
                    malicious_engines = vt_result.get("malicious", 0)
                    if malicious_engines > 0:
                        is_virus = True
                        score = max(score, min(40 + (malicious_engines * 15), 100))
                        reasons.append(f"VirusTotal: {malicious_engines} ta antivirus buni virus deb tasdiqladi!")

                # Agar evristika yoki VirusTotal yuqori xavf aniqlasa
                if score >= 60 or is_virus:
                    # Zararli faylni o'chiramiz
                    await safe_delete_message(update)
                    
                    full_name = get_full_name(user)
                    reasons_text = "\n".join([f"• {r}" for r in reasons[:4]])
                    
                    await notify_chat_after_delete(
                        update,
                        f"🗑 <b>Zararli APK fayl o‘chirildi!</b>\n\n"
                        f"Foydalanuvchi: <b>{full_name}</b>\n"
                        f"Fayl nomi: <code>{file_name}</code>\n"
                        f"Xavf darajasi: <b>HIGH (Ball: {score})</b>\n\n"
                        f"<b>Aniqlangan sabablar:</b>\n{reasons_text}"
                    )
                    
                    # Log kanalga xabar yuborish (ixtiyoriy, agar tizimingizda bo'lsa)
                    log_chat_id = settings.get("log_channel")
                    if log_chat_id:
                        from bot.moderation import send_log_message
                        await send_log_message(
                            context, 
                            log_chat_id, 
                            f"🛡 <b>SecureBot APK Log</b>\n\n<b>Guruh:</b> {chat.title}\n<b>User:</b> {full_name}\n<b>Fayl:</b> {file_name}\n<b>O'chirildi:</b> Ha"
                        )
                    return
                else:
                    # Agar fayl toza bo'lsa, foydalanuvchiga xabar berish (ixtiyoriy)
                    await message.reply_html(f"✅ <b>Fayl tekshirildi (Xavfsiz):</b> <code>{file_name}</code>\nHech qanday virus aniqlanmadi.")

            finally:
                # Vaqtinchalik faylni tozalash
                try:
                    os.remove(path)
                except OSError:
                    pass
  
    if chat.type == "private":
        return

    settings = get_settings(chat.id)

    if not settings["enabled"]:
        return

    if is_whitelisted(chat.id, user.id):
        return

    text = message.text or message.caption or ""
    urls = extract_urls(text)

    if urls and any(is_blacklisted_url(chat.id, url) for url in urls):
        deleted = await safe_delete_message(update)
        if deleted:
            await notify_chat_after_delete(
                update,
                "🗑 <b>Blacklisted link detected</b>\n\nThe message was deleted because it contained a link that has been added to the blacklist."
            )
        return

    if settings["scan_links"]:
        link_result = await scan_links_in_text(text)
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
        # Handle mute/ban actions if configured
        if settings["mute_high_risk"] or settings["ban_high_risk"]:
            await handle_user_restriction(
                update,
                chat,
                user,
                settings,
                result,
                full_name
            )
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

async def handle_user_restriction(
    update: Update,
    chat,
    user,
    settings: dict,
    result: dict,
    full_name: str,
):
    """Handle muting or banning a user for sharing high-risk content."""
    from telegram.constants import ChatPermissions
    
    try:
        if settings["ban_high_risk"]:
            # Ban the user
            await chat.ban_member(user.id)
            await notify_chat_after_delete(
                update,
                (
                    f"🚫 <b>User Banned</b>\n\n"
                    f"User: <b>{full_name}</b>\n"
                    f"Reason: Shared high-risk link\n"
                    f"Risk Score: <b>{result['score']}</b>"
                )
            )
        elif settings["mute_high_risk"]:
            # Mute the user (restrict to text only, no media)
            await chat.restrict_member(
                user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            await notify_chat_after_delete(
                update,
                (
                    f"🔇 <b>User Muted</b>\n\n"
                    f"User: <b>{full_name}</b>\n"
                    f"Reason: Shared high-risk link\n"
                    f"Risk Score: <b>{result['score']}</b>"
                )
            )
    except TelegramError as e:
        # Log error but don't crash
        pass