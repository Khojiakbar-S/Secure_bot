import asyncio
import threading
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app import main as run_bot
from webapp import create_web_server
from config import BOT_TOKEN, WEB_HOST, WEB_PORT
from telegram import Bot


def run_web_server():
    """Run the web server in a separate thread."""
    print(f"🚀 Starting SecureBot Web Server on {WEB_HOST}:{WEB_PORT}")
    bot = Bot(token=BOT_TOKEN)
    server = create_web_server(bot, WEB_HOST, WEB_PORT)

    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(server.start())
    except KeyboardInterrupt:
        print("Stopping web server...")
    finally:
        loop.close()


def main():
    """Main entry point that runs both bot and web server."""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN topilmadi. .env faylni tekshiring.")

    print("🤖 Starting Telegram Bot...")
    print("🌐 Starting Web Server in background thread...")

    # Start web server in a separate thread
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Run bot in main thread (this will block)
    try:
        run_bot()
    except KeyboardInterrupt:
        print("Shutting down...")


if __name__ == "__main__":
    main()