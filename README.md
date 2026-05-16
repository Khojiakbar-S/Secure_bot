# SecureBot

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Telegram API](https://img.shields.io/badge/Telegram_API-blueviolet)
![SQLite](https://img.shields.io/badge/SQLite-lightgrey)
![Docker](https://img.shields.io/badge/Docker-blue)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-teal)
![aiohttp](https://img.shields.io/badge/aiohttp-asyncio-green)

---

## Overview

SecureBot is a modern Telegram group security and moderation bot built for active communities. It protects groups from malicious links and APK files while providing admins with a private Mini App dashboard for centralized configuration.

The architecture combines a Telegram bot service with an `aiohttp` web server and a zero-dependency frontend dashboard. Strong cryptographic validation ensures only authorized admin sessions can access and update group settings.

---

## Key Features

- ✅ Real-time link scanning and threat detection
- ✅ APK file inspection controls for group safety
- ✅ Private Telegram Mini App admin dashboard
- ✅ `tg.initData` cryptographic validation using HMAC-SHA256
- ✅ Dashboard restricted to Telegram private chats (DM only)
- ✅ Dynamic group selector for admins managing multiple chats
- ✅ Per-group settings stored securely in SQLite
- ✅ Blacklist manager for blocked URLs via the dashboard
- ✅ Manual database backup & restore via `/backup` and `/restore`
- ✅ Zero-dependency frontend with Vanilla JS, HTML, and Tailwind CSS via CDN
- ✅ Docker-ready deployment with persistent SQLite storage

---

## Architecture

SecureBot is designed as a hybrid Python service:

- `main.py` starts the Telegram bot and launches the web server in a background thread.
- `webapp.py` hosts the Mini App API and serves the dashboard UI from `index.html`.
- `bot/database.py` stores chat settings, whitelists, blacklists, and cached scan results in SQLite.
- `bot/commands.py` implements bot commands, dashboard launch flow, blacklist controls, and admin features.
- `index.html` provides a secure Web App UI for authorized admins.

### Data flow

1. Admin opens SecureBot in a private Telegram chat.
2. The bot presents a Mini App dashboard button.
3. The dashboard frontend sends `tg.initData` to the backend.
4. The backend verifies the payload signature with the bot token.
5. If valid, the dashboard loads authorized groups and settings.
6. Changes are saved to SQLite and applied immediately.

---

## Screenshots

![Dashboard](link_to_dashboard_screenshot)
![Group Selector](link_to_group_selection_screenshot)
![Settings Panel](link_to_settings_screenshot)

---

## Local Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/securebot.git
cd securebot
```

### 2. Copy and configure the environment file

```bash
cp .env.example .env
```

Update `.env` with the following values:

```env
BOT_TOKEN=your_bot_token_here
BOT_OWNER_ID=your_telegram_user_id
DB_PATH=securebot.db
WEB_HOST=0.0.0.0
WEB_PORT=8080
WEB_APP_URL=https://your-domain.com
GOOGLE_SAFE_BROWSING_API_KEY=
```

### 3. Install dependencies

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

### 4. Test the Web App locally with ngrok

```bash
ngrok http 8080
```

Update `WEB_APP_URL` in `.env` to the secure ngrok URL provided.

### 5. Run SecureBot

```bash
python main.py
```

---

## Docker Deployment

SecureBot can be deployed with Docker Compose for a production-ready setup.

### 1. Build and start

```bash
docker compose up --build -d
```

### 2. View logs

```bash
docker compose logs -f securebot
```

### 3. Persistent storage

The SQLite database is persisted using the `securebot_data` Docker volume at `/app/data/securebot.db`.

### 4. Environment handling

`docker-compose.yml` loads `.env` and configures:

- `PYTHONUNBUFFERED=1`
- `DB_PATH=/app/data/securebot.db`

---

## Project Structure

- `main.py` — bot + web server launcher
- `webapp.py` — dashboard API and Web App auth
- `config.py` — environment and runtime configuration
- `index.html` — private Mini App dashboard UI
- `Dockerfile` — container build instructions
- `docker-compose.yml` — container orchestration with persistence
- `bot/commands.py` — Telegram command handlers and dashboard entrypoint
- `bot/database.py` — SQLite storage, settings, and whitelist management
- `bot/texts.py` — response templates and help text

---

## Notes

- The Mini App dashboard is intentionally limited to private Telegram chats for enhanced security.
- Cryptographic validation of `tg.initData` prevents unauthorized interface access.
- SQLite provides lightweight, persistent storage for settings and scan history.

---

## Recommended next steps

- Replace screenshot placeholders with real dashboard images
- Secure `WEB_APP_URL` with a production HTTPS endpoint
- Add a `GOOGLE_SAFE_BROWSING_API_KEY` for enhanced link scanning
- Use `/blacklist` by replying to a message containing a URL to block that link across the group
- Use `/backup` to download the SQLite database and `/restore` with a document caption to restore it
- Confirm the bot has required Telegram admin permissions in groups
