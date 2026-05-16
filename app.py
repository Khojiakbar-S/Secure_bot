import os
import asyncio
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import BOT_TOKEN
from bot.database import init_db
from bot.commands import (
    start_command,
    help_command,
    settings_command,
    dashboard_command,
    setlog_command,
    whitelist_command,
    blacklist_command,
    backup_command,
    restore_handler,
    button_callback,
)
from bot.group_messages import handle_group_messages

# Veb-serverni loyihaga olib kiramiz
from webapp import create_web_server

async def start_bot_and_server():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN topilmadi. .env faylni tekshiring.")

    # 1. Bazani ishga tushiramiz
    init_db()

    # 2. Telegram Botni quramiz
    app = Application.builder().token(BOT_TOKEN).build()

    # Handlerlarni qo'shamiz
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("setlog", setlog_command))
    app.add_handler(CommandHandler("whitelist", whitelist_command))
    app.add_handler(CommandHandler("blacklist", blacklist_command))
    app.add_handler(CommandHandler("backup", backup_command))
    app.add_handler(MessageHandler(filters.Document.ALL, restore_handler))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & ~filters.COMMAND,
            handle_group_messages
        )
    )

    # 3. Railway portlarini o'qiymiz (PORT o'zgaruvchisi orqali)
    host = os.environ.get("WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8080))  # Railway o'rnatgan dynamic PORT

    # 4. Veb-serverni yaratamiz
    web_server = create_web_server(app.bot, host=host, port=port)

    # 5. Bot va Veb-serverni bir vaqtda parallel ishga tushiramiz
    print(f"SecureBot va Web App {host}:{port} portida ishga tushmoqda...")
    
    await app.initialize()
    await app.updater.start_polling()
    await app.start()
    
    # Veb-serverni ishga tushirib, dasturni ushlab turamiz
    await web_server.start()

def main():
    # Asinxron loopni boshlash
    asyncio.run(start_bot_and_server())

if __name__ == "__main__":
    main()