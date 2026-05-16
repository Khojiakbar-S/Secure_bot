import asyncio
import hashlib
import hmac
import json
import os
from pathlib import Path
from urllib.parse import unquote

from aiohttp import web
from aiohttp.web_fileresponse import FileResponse
from telegram import Bot
from telegram.error import TelegramError

from bot.database import (
    get_settings,
    update_setting,
    add_whitelist,
    remove_whitelist,
    list_whitelist,
    add_blacklist,
    remove_blacklist,
    list_blacklist,
    get_statistics,
    list_group_chat_ids,
)


class TelegramAuth:
    """Handle Telegram Web App authentication."""

    @staticmethod
    def validate_init_data(init_data: str, bot_token: str) -> dict:
        """Validate Telegram initData and return parsed data."""
        if not init_data:
            raise ValueError("No initData provided")

        # 1. Ma'lumotlarni xavfsiz va aniq ajratib olish (parse_qs siz)
        pairs = init_data.split('&')
        data = {}
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                data[key] = unquote(value)

        # 2. Xesh borligini tekshirish
        if 'hash' not in data:
            raise ValueError("No hash in initData")

        received_hash = data.pop('hash')

        # 3. Xeshni tekshirish uchun ma'lumotlarni Telegram qoidasiga ko'ra terish
        data_string = '\n'.join(f"{k}={v}" for k, v in sorted(data.items()))

        # 4. Kriptografik tekshiruv kalitini yaratish
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode(),
            digestmod=hashlib.sha256
        ).digest()

        # 5. Kutilayotgan xeshni hisoblash
        expected_hash = hmac.new(
            key=secret_key,
            msg=data_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(received_hash, expected_hash):
            raise ValueError("Invalid hash")

        # 6. JSON formatlash (oldingi xatoni oldini olish uchun)
        if 'user' in data and isinstance(data['user'], str):
            try:
                data['user'] = json.loads(data['user'])
            except Exception:
                pass

        return data


class WebAppServer:
    """Telegram Web App server using aiohttp."""

    def __init__(self, bot: Bot, host: str = '0.0.0.0', port: int = 8080):
        self.bot = bot
        self.bot_token = bot.token
        self.host = host
        self.port = port
        self.app = web.Application()
        self.auth = TelegramAuth()
        self.setup_routes()

    def setup_routes(self):
        """Setup web routes."""
        self.app.router.add_get('/', self.serve_index)
        self.app.router.add_get('/api/my-groups', self.get_my_groups)
        self.app.router.add_get('/api/settings', self.get_settings)
        self.app.router.add_post('/api/settings', self.update_settings)

    async def serve_index(self, request):
        """Serve the main HTML file."""
        html_path = Path(__file__).parent / 'index.html'
        if not html_path.exists():
            raise web.HTTPNotFound()

        return FileResponse(html_path)

    async def get_settings(self, request):
        """Get settings and whitelist for a chat."""
        try:
            chat_id = request.query.get('chat_id')
            init_data = request.query.get('init_data')

            if not chat_id or not init_data:
                return web.json_response({'error': 'Missing chat_id or init_data'}, status=400)

            auth_data = self.auth.validate_init_data(init_data, self.bot_token)
            user_id = auth_data.get('user', {}).get('id')
            if not user_id:
                return web.json_response({'error': 'Invalid user data'}, status=401)

            chat_id_int = int(chat_id)
            settings = get_settings(chat_id_int)
            whitelist = list_whitelist(chat_id_int)
            blacklist = list_blacklist(chat_id_int)
            stats = get_statistics()

            return web.json_response({
                'settings': settings,
                'whitelist': whitelist,
                'blacklist': blacklist,
                'stats': stats
            })

        except ValueError as e:
            return web.json_response({'error': str(e)}, status=401)
        except Exception as e:
            print(f"Error in get_settings: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)

    async def get_my_groups(self, request):
        """Return groups where the bot is present and the user is an admin."""
        try:
            init_data = request.query.get('init_data')
            if not init_data:
                return web.json_response({'error': 'Missing init_data'}, status=400)

            auth_data = self.auth.validate_init_data(init_data, self.bot_token)
            user_id = auth_data.get('user', {}).get('id')
            if not user_id:
                return web.json_response({'error': 'Invalid user data'}, status=401)

            groups = []
            for chat_id in list_group_chat_ids():
                try:
                    member = await self.bot.get_chat_member(chat_id, user_id)
                    if member.status in ("administrator", "creator"):
                        title = None
                        try:
                            chat = await self.bot.get_chat(chat_id)
                            title = getattr(chat, 'title', None)
                        except TelegramError:
                            title = None

                        groups.append({
                            'chat_id': chat_id,
                            'chat_title': title or f'Group {chat_id}'
                        })
                except TelegramError:
                    continue

            return web.json_response({'groups': groups})

        except ValueError as e:
            return web.json_response({'error': str(e)}, status=401)
        except Exception as e:
            print(f"Error in get_my_groups: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)

    async def update_settings(self, request):
        """Update settings or whitelist."""
        try:
            # Get JSON data
            data = await request.json()

            chat_id = data.get('chat_id')
            init_data = data.get('init_data')

            if not chat_id or not init_data:
                return web.json_response({'error': 'Missing chat_id or init_data'}, status=400)

            # Validate Telegram auth
            auth_data = self.auth.validate_init_data(init_data, self.bot_token)

            # Check if user is admin
            user_id = auth_data.get('user', {}).get('id')
            if not user_id:
                return web.json_response({'error': 'Invalid user data'}, status=401)

            chat_id_int = int(chat_id)
            response_data = {}

            # Handle settings update
            if 'settings' in data:
                settings = data['settings']
                allowed_keys = {
                    'enabled', 'delete_high', 'warn_medium', 'reply_low',
                    'scan_links', 'scan_apk', 'mute_high_risk', 'ban_high_risk'
                }

                for key, value in settings.items():
                    if key in allowed_keys:
                        update_setting(chat_id_int, key, int(value))

                response_data['settings_updated'] = True

            # Handle whitelist add
            if 'add_whitelist' in data:
                user_id_to_add = int(data['add_whitelist'])
                added = add_whitelist(chat_id_int, user_id_to_add)
                response_data['added'] = added

            # Handle whitelist remove
            if 'remove_whitelist' in data:
                user_id_to_remove = int(data['remove_whitelist'])
                removed = remove_whitelist(chat_id_int, user_id_to_remove)
                response_data['removed'] = removed

            # Handle blacklist add
            if 'add_blacklist' in data:
                url_to_add = str(data['add_blacklist']).strip()
                blacklisted = add_blacklist(chat_id_int, url_to_add)
                response_data['blacklisted'] = blacklisted

            # Handle blacklist remove
            if 'remove_blacklist' in data:
                url_to_remove = str(data['remove_blacklist']).strip()
                removed_blacklist = remove_blacklist(chat_id_int, url_to_remove)
                response_data['removed_blacklist'] = removed_blacklist

            return web.json_response(response_data)

        except ValueError as e:
            return web.json_response({'error': str(e)}, status=401)
        except Exception as e:
            print(f"Error in update_settings: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)

    async def start(self):
        """Start the web server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"Web server started on http://{self.host}:{self.port}")

        # Keep the server running
        try:
            while True:
                await asyncio.sleep(3600)  # Sleep for an hour
        except asyncio.CancelledError:
            print("Web server shutting down...")
            await runner.cleanup()
            raise
        except Exception as e:
            print(f"Web server error: {e}")
            await runner.cleanup()
            raise


# Factory function to create and start the server
def create_web_server(bot: Bot, host: str = '0.0.0.0', port: int = 8080):
    """Create a WebAppServer instance."""
    return WebAppServer(bot, host, port)


if __name__ == "__main__":
    # For testing the web server standalone
    import sys
    sys.path.append(str(Path(__file__).parent))

    from config import BOT_TOKEN

    if not BOT_TOKEN:
        print("BOT_TOKEN not found in environment variables")
        sys.exit(1)

    host = os.environ.get("WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("WEB_PORT", "8080"))

    server = create_web_server(BOT_TOKEN, host=host, port=port)
    asyncio.run(server.start())