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


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN topilmadi. .env faylni tekshiring.")

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

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

    print("SecureBot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()