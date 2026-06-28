# 🎵 Telegram Voice Chat Music Bot

A **production-ready**, fully-featured Telegram Group Voice Chat Music Bot written in Python.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-2.0-green.svg)](https://pyrogram.org)
[![PyTgCalls](https://img.shields.io/badge/PyTgCalls-0.9-orange.svg)](https://pytgcalls.github.io)

---

## 📋 Features

| Category | Features |
|---|---|
| 🎵 **Playback** | YouTube search, direct URL, auto-join VC, progress bar |
| 📋 **Queue** | Unlimited queue, shuffle, loop, skip, clear |
| 🎤 **Search** | Interactive YouTube search with result selection |
| 📀 **Playlists** | Create, manage, and play personal playlists |
| 🔊 **Controls** | Pause, Resume, Volume, inline keyboard panel |
| 🎤 **Lyrics** | Fetch lyrics via Genius API |
| 🏠 **Multi-group** | Supports unlimited groups simultaneously |
| 🔄 **Auto-reconnect** | Reconnects if kicked from VC |
| 🚪 **Auto-leave** | Leaves VC after configurable inactivity timeout |
| 🗄️ **Database** | SQLite (dev) / PostgreSQL (prod), Alembic migrations |
| ☁️ **Render-ready** | Docker + render.yaml + health check included |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- FFmpeg installed on system
- Telegram account (for session string)
- Bot token from [@BotFather](https://t.me/BotFather)
- API credentials from [my.telegram.org](https://my.telegram.org)

### 1. Clone and Configure

```bash
git clone <your-repo-url>
cd musicbot
cp .env.example .env
```

Edit `.env` with your credentials (see [Environment Variables](#-environment-variables) below).

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Generate Session String

The bot uses **two** Telegram clients:
- `bot` — handles commands (uses `BOT_TOKEN`)
- `assistant` — joins voice chats (uses `SESSION_STRING`)

Generate the session string:

```python
from pyrogram import Client

async def main():
    async with Client("session", api_id=YOUR_API_ID, api_hash="YOUR_API_HASH") as app:
        print(await app.export_session_string())

import asyncio
asyncio.run(main())
```

Copy the printed string into `SESSION_STRING` in your `.env`.

### 4. Run Locally

```bash
python main.py
```

---

## 🤖 BotFather Setup

1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot: `/newbot`
3. Copy the token to `BOT_TOKEN`
4. Set bot commands: `/setcommands`
5. Paste these commands:

```
start - Start the bot
help - Show all commands
play - Play a song or YouTube URL
pause - Pause playback
resume - Resume playback
skip - Skip current song
stop - Stop and clear queue
queue - View current queue
shuffle - Toggle shuffle mode
loop - Toggle loop mode
volume - Set volume (1-200)
search - Search YouTube
lyrics - Get song lyrics
playlist - Manage playlists
clear - Clear the queue
nowplaying - Show current song
ping - Check bot latency
stats - Bot statistics
settings - Group settings
```

6. Grant the bot admin permissions in your group with:
   - ✅ Manage Voice Chats

---

## 🎮 Commands Reference

### Playback
| Command | Description |
|---|---|
| `/play Believer` | Search and play a song |
| `/play https://youtu.be/...` | Play from YouTube URL |
| `/play https://youtube.com/playlist?list=...` | Queue entire playlist |
| `/pause` | Pause playback |
| `/resume` | Resume playback |
| `/skip` | Skip current song |
| `/stop` | Stop and leave voice chat |
| `/nowplaying` | Show current song with progress |

### Queue
| Command | Description |
|---|---|
| `/queue` | View current queue |
| `/clear` | Clear all queued songs |
| `/shuffle` | Toggle shuffle mode |
| `/loop` | Toggle loop mode |

### Search & Discovery
| Command | Description |
|---|---|
| `/search <query>` | Interactive YouTube search |
| `/lyrics` | Get lyrics for current song |
| `/lyrics <song>` | Get lyrics for any song |

### Playlists
| Command | Description |
|---|---|
| `/playlist` | List your playlists |
| `/playlist create <name>` | Create a playlist |
| `/playlist add <name>` | Add current song to playlist |
| `/playlist play <name>` | Queue an entire playlist |
| `/playlist delete <name>` | Delete a playlist |

### Info & Settings
| Command | Description |
|---|---|
| `/ping` | Bot latency |
| `/stats` | Usage statistics |
| `/volume 80` | Set volume (1-200) |
| `/settings` | Group settings panel |

---

## 🔧 Environment Variables

Create a `.env` file based on `.env.example`:

| Variable | Required | Description |
|---|---|---|
| `API_ID` | ✅ | Telegram API ID from my.telegram.org |
| `API_HASH` | ✅ | Telegram API Hash |
| `BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `SESSION_STRING` | ✅ | Pyrogram StringSession for voice chats |
| `DATABASE_URL` | ✅ | SQLite or PostgreSQL URL |
| `REDIS_URL` | ❌ | Redis URL (optional, for rate limiting) |
| `LOG_LEVEL` | ❌ | Logging level (default: INFO) |
| `MAX_QUEUE_SIZE` | ❌ | Max songs per queue (default: 50, 0=unlimited) |
| `AUTO_LEAVE_TIMEOUT` | ❌ | Seconds before auto-leave (default: 300) |
| `DEFAULT_VOLUME` | ❌ | Default volume (default: 100) |
| `OWNER_ID` | ❌ | Your Telegram user ID for owner commands |
| `PORT` | ❌ | Health check port (default: 8080) |
| `GENIUS_TOKEN` | ❌ | Genius API key for lyrics |

---

## ☁️ Deploying on Render

### Step 1: Prepare Repository

Push your code to GitHub (make sure `.env` is in `.gitignore`).

### Step 2: Create Render Account

Sign up at [render.com](https://render.com).

### Step 3: Create a New Web Service

1. Click **New** → **Web Service**
2. Connect your GitHub repository
3. Select **Docker** as the environment
4. Render will auto-detect `render.yaml`

### Step 4: Set Environment Variables

In the Render dashboard → **Environment**:

```
API_ID          = <your API ID>
API_HASH        = <your API hash>
BOT_TOKEN       = <your bot token>
SESSION_STRING  = <your session string>
DATABASE_URL    = postgresql+asyncpg://<from Render PostgreSQL>
PORT            = 10000
ON_RENDER       = true
LOG_LEVEL       = INFO
```

### Step 5: Add PostgreSQL Database

1. Click **New** → **PostgreSQL**
2. Name it `musicbot-db`
3. Copy the **Internal Database URL** and set as `DATABASE_URL`
   - Change `postgresql://` → `postgresql+asyncpg://`

### Step 6: Deploy

Click **Deploy**. The bot will:
1. Build the Docker image (includes FFmpeg)
2. Run Alembic migrations
3. Start the bot

### Step 7: Verify

- Check health: `https://your-service.onrender.com/health`
- Add bot to a Telegram group
- Grant admin permissions
- Start a voice chat
- Send `/play Believer`

### Important Notes for Render Free Tier

⚠️ **Free tier services sleep after 15 minutes of inactivity.**

To keep the bot alive:
- Use [UptimeRobot](https://uptimerobot.com) to ping `/ping` every 5 minutes
- Or upgrade to a paid plan

---

## 🐳 Docker Deployment (Self-hosted)

```bash
# Build image
docker build -t musicbot .

# Run with environment file
docker run -d \
  --name musicbot \
  --env-file .env \
  -p 8080:8080 \
  -v $(pwd)/storage:/app/storage \
  -v $(pwd)/logs:/app/logs \
  musicbot
```

---

## 🏗️ Project Structure

```
musicbot/
├── app/
│   ├── bot/
│   │   ├── commands/         # Command handlers (/play, /skip, etc.)
│   │   ├── filters/          # Custom Pyrogram filters
│   │   ├── handlers/         # Callback queries, error handler
│   │   └── middlewares/      # Rate limiting, group registration
│   ├── config/               # Settings (Pydantic), logging
│   ├── database/
│   │   ├── models/           # SQLAlchemy ORM models
│   │   └── routers/          # CRUD operations
│   ├── player/
│   │   ├── downloader.py     # yt-dlp audio downloader
│   │   ├── queue.py          # In-memory queue manager
│   │   └── voice/
│   │       └── engine.py     # PyTgCalls voice engine
│   ├── services/
│   │   ├── health.py         # FastAPI health check API
│   │   └── music_service.py  # Core orchestration service
│   └── utils/
│       ├── formatters.py     # Progress bars, message formatting
│       ├── keyboards.py      # InlineKeyboard builders
│       ├── lyrics.py         # Lyrics fetcher
│       ├── thumbnail.py      # Thumbnail downloader
│       └── validators.py     # URL/input validation
├── alembic/                  # Database migrations
├── storage/temp/             # Temporary audio files
├── logs/                     # Log files
├── main.py                   # Entry point
├── requirements.txt
├── Dockerfile
├── render.yaml
├── Procfile
└── .env.example
```

---

## 🗄️ Database Schema

| Table | Purpose |
|---|---|
| `users` | Registered Telegram users |
| `groups` | Registered Telegram groups |
| `queue` | Current playback queue per group |
| `history` | Play history per group |
| `playlists` | User-created playlists |
| `playlist_items` | Songs within playlists |
| `admins` | Bot admin assignments |
| `group_settings` | Key-value group configuration |

---

## 🔒 Security

- Rate limiting: Token bucket per user (5 requests/5s)
- Admin-only commands: pause, skip, stop, clear, volume, settings
- Input sanitization: All queries cleaned before use
- SQL injection: Prevented via SQLAlchemy ORM (parameterized queries)
- Flood protection: FloodWait handled automatically

---

## 📊 Architecture

```
User → /play <song>
         │
         ▼
    [Bot Command Handler]
         │
         ▼
    [Music Service]
     ├── [Downloader] → yt-dlp → FFmpeg → temp file
     ├── [Queue Manager] → in-memory + DB queue
     └── [Voice Engine] → PyTgCalls → Telegram VC
              │
              ▼
         [On Stream End]
              │
              ▼
    [Next Song / Auto-leave]
```

---

## 🐛 Troubleshooting

### Bot doesn't join voice chat
- Ensure the assistant account (SESSION_STRING) is a member of the group
- Grant the **bot** admin permissions with "Manage Voice Chats"
- Start a voice chat first before using `/play`

### Download errors
- Check FFmpeg is installed: `ffmpeg -version`
- Verify yt-dlp is up to date: `pip install -U yt-dlp`
- Some songs may be geo-restricted or age-restricted

### Session expired
- Regenerate `SESSION_STRING` using the Python script above

### Database errors
- SQLite: Ensure the file path is writable
- PostgreSQL: Verify `DATABASE_URL` uses `postgresql+asyncpg://`

---

## 📜 License

MIT License — Feel free to use and modify.

---

## 🙏 Credits

- [Pyrogram](https://pyrogram.org) — Telegram MTProto client
- [PyTgCalls](https://pytgcalls.github.io) — Voice chat streaming
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — YouTube downloader
- [FastAPI](https://fastapi.tiangolo.com) — Health check API
- [SQLAlchemy](https://sqlalchemy.org) — Database ORM
