"""
/playlist command — manage user playlists.

Subcommands:
  /playlist              — List your playlists
  /playlist create <name> — Create a new playlist
  /playlist add <name>    — Add current song to a playlist
  /playlist play <name>   — Queue a playlist for playback
  /playlist delete <name> — Delete a playlist
"""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from app.bot.filters import not_banned
from app.database import get_session
from app.database.routers import playlists as playlist_crud
from app.database.routers import users as user_crud
from app.player.queue import queue_manager
from app.services.music_service import music_service
from app.utils.keyboards import playlist_keyboard


@Client.on_message(filters.command("playlist") & not_banned)
async def playlist_command(client: Client, message: Message) -> None:
    """Handle all /playlist subcommands."""
    if not message.from_user:
        return

    args = message.text.split(maxsplit=2)
    user = message.from_user

    # /playlist (no args) — list playlists
    if len(args) < 2:
        await _list_playlists(message, user.id)
        return

    sub = args[1].lower()

    if sub == "create":
        if len(args) < 3:
            await message.reply(
                "❌ Provide a playlist name.\n"
                "Usage: <code>/playlist create My Favorites</code>"
            )
            return
        await _create_playlist(message, user.id, args[2].strip())

    elif sub == "add":
        if len(args) < 3:
            await message.reply(
                "❌ Provide a playlist name.\n"
                "Usage: <code>/playlist add My Favorites</code>"
            )
            return
        await _add_current_to_playlist(message, user.id, args[2].strip())

    elif sub == "play":
        if len(args) < 3:
            await message.reply(
                "❌ Provide a playlist name.\n"
                "Usage: <code>/playlist play My Favorites</code>"
            )
            return
        await _play_playlist(message, user.id, args[2].strip())

    elif sub == "delete":
        if len(args) < 3:
            await message.reply(
                "❌ Provide a playlist name.\n"
                "Usage: <code>/playlist delete My Favorites</code>"
            )
            return
        await _delete_playlist(message, user.id, args[2].strip())

    else:
        await message.reply(
            "❌ Unknown subcommand.\n\n"
            "Available: <code>create</code>, <code>add</code>, "
            "<code>play</code>, <code>delete</code>"
        )


async def _list_playlists(message: Message, tg_id: int) -> None:
    async with get_session() as session:
        playlists = await playlist_crud.get_user_playlists(session, tg_id)

    if not playlists:
        await message.reply(
            "📭 You have no playlists yet.\n\n"
            "Create one with: <code>/playlist create My Favorites</code>"
        )
        return

    lines = ["📀 <b>Your Playlists</b>\n"]
    for pl in playlists:
        lines.append(f"• <b>{pl.name}</b>")
    await message.reply("\n".join(lines))


async def _create_playlist(message: Message, tg_id: int, name: str) -> None:
    if len(name) > 64:
        await message.reply("❌ Playlist name is too long (max 64 characters).")
        return

    async with get_session() as session:
        # Ensure user exists
        await user_crud.get_or_create_user(
            session, tg_id,
            first_name=message.from_user.first_name or "User",
            username=message.from_user.username,
        )
        pl = await playlist_crud.create_playlist(session, tg_id, name)

    if pl:
        await message.reply(f"✅ Playlist <b>{name}</b> created!")
    else:
        await message.reply("❌ Could not create playlist. Please /start the bot first.")


async def _add_current_to_playlist(
    message: Message, tg_id: int, playlist_name: str
) -> None:
    chat = message.chat
    if not chat or chat.type.name not in ("GROUP", "SUPERGROUP"):
        await message.reply("❌ This command must be used in a group.")
        return

    gq = await queue_manager.get(chat.id)
    current = await gq.get_current()
    if current is None:
        await message.reply("❌ No song is currently playing.")
        return

    song = current.song

    async with get_session() as session:
        playlists = await playlist_crud.get_user_playlists(session, tg_id)
        target = next((p for p in playlists if p.name.lower() == playlist_name.lower()), None)
        if target is None:
            await message.reply(
                f"❌ Playlist <b>{playlist_name}</b> not found.\n"
                f"Create it first: <code>/playlist create {playlist_name}</code>"
            )
            return
        await playlist_crud.add_item_to_playlist(
            session=session,
            playlist_id=target.id,
            title=song.title,
            url=song.url,
            duration=song.duration,
            video_id=song.video_id,
            thumbnail=song.thumbnail,
            uploader=song.uploader,
        )

    await message.reply(
        f"✅ Added <b>{song.title}</b> to playlist <b>{playlist_name}</b>."
    )


async def _play_playlist(message: Message, tg_id: int, playlist_name: str) -> None:
    if not message.chat or message.chat.type.name not in ("GROUP", "SUPERGROUP"):
        await message.reply("❌ This command must be used in a group.")
        return

    async with get_session() as session:
        playlists = await playlist_crud.get_user_playlists(session, tg_id)
        target = next((p for p in playlists if p.name.lower() == playlist_name.lower()), None)
        if target is None:
            await message.reply(f"❌ Playlist <b>{playlist_name}</b> not found.")
            return
        pl_with_items = await playlist_crud.get_playlist_with_items(session, target.id)

    if not pl_with_items or not pl_with_items.items:
        await message.reply(f"📭 Playlist <b>{playlist_name}</b> is empty.")
        return

    user = message.from_user
    requested_by = f"@{user.username}" if user.username else user.first_name
    chat_id = message.chat.id
    count = 0

    status = await message.reply(
        f"📀 Queuing <b>{len(pl_with_items.items)}</b> songs from <b>{playlist_name}</b>..."
    )

    from app.player.downloader import SongInfo
    from app.player.queue import queue_manager as qm
    from app.database.routers import queue as queue_crud

    for item in pl_with_items.items:
        song = SongInfo(
            title=item.title,
            url=item.url,
            video_id=item.video_id,
            thumbnail=item.thumbnail,
            duration=item.duration,
            uploader=item.uploader,
        )
        gq = await qm.get(chat_id)
        await gq.add(song)
        async with get_session() as session:
            await queue_crud.add_to_queue(
                session=session,
                chat_id=chat_id,
                title=song.title,
                url=song.url,
                duration=song.duration,
                requested_by_id=user.id,
                requested_by_name=requested_by,
                video_id=song.video_id,
                thumbnail=song.thumbnail,
                uploader=song.uploader,
            )
        count += 1

    from app.player.voice.engine import voice_engine
    if not voice_engine.is_active(chat_id):
        import asyncio
        asyncio.create_task(music_service._start_playback(chat_id))

    await status.edit(
        f"✅ Queued <b>{count}</b> songs from playlist <b>{playlist_name}</b>."
    )


async def _delete_playlist(message: Message, tg_id: int, playlist_name: str) -> None:
    async with get_session() as session:
        playlists = await playlist_crud.get_user_playlists(session, tg_id)
        target = next((p for p in playlists if p.name.lower() == playlist_name.lower()), None)
        if target is None:
            await message.reply(f"❌ Playlist <b>{playlist_name}</b> not found.")
            return
        deleted = await playlist_crud.delete_playlist(session, target.id)

    if deleted:
        await message.reply(f"🗑 Playlist <b>{playlist_name}</b> deleted.")
    else:
        await message.reply("❌ Could not delete playlist.")
