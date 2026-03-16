from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes


async def safe_reply_html(update: Update, text: str):
    try:
        await update.effective_message.reply_html(text, disable_web_page_preview=True)
    except TelegramError:
        pass


async def safe_delete_message(update: Update) -> bool:
    try:
        await update.effective_message.delete()
        return True
    except TelegramError:
        return False


async def send_log_message(
    context: ContextTypes.DEFAULT_TYPE,
    log_chat_id: str | None,
    text: str,
):
    if not log_chat_id:
        return

    try:
        await context.bot.send_message(
            chat_id=log_chat_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except TelegramError:
        pass