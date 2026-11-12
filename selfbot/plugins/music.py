"""Music plugin: `.song <query>` searches YouTube via yt-dlp and sends the audio."""
import logging
import tempfile
from pathlib import Path

from telethon import events

from selfbot.config import config

log = logging.getLogger("selfbot.music")


def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}song (.+)$"))
    async def song_cmd(event: events.NewMessage.Event) -> None:
        query = event.pattern_match.group(1).strip()
        if not query:
            return
        try:
            import yt_dlp
        except ImportError:
            await event.edit("❌ `yt-dlp` missing. Run: `pip install yt-dlp`")
            return

        await event.edit(f"🔎 Searching: `{query}` ...")
        tmpdir = Path(tempfile.mkdtemp(dir=config.DOWNLOAD_DIR))
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(tmpdir / "%(title).80s.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "default_search": "ytsearch1",
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                if "entries" in info:
                    info = info["entries"][0]
                title = info.get("title", "audio")
                mp3 = next(tmpdir.glob("*.mp3"), None)
                if not mp3:
                    await event.edit("❌ Download failed.")
                    return
                await event.client.send_file(
                    event.chat_id,
                    str(mp3),
                    caption=f"🎵 **{title}**",
                    reply_to=event.reply_to_msg_id,
                )
                await event.delete()
        except Exception as exc:  # noqa: BLE001
            log.exception("Music failed: %s", exc)
            await event.edit(f"❌ `{exc}`")
