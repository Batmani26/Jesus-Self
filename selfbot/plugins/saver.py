"""Timed media saver — saves self-destructing photos/videos to disk.

Telegram never gives the original file bytes for secret/timed media, so we
save a screenshot of the rendered media instead (same approach as most
selfbots).
"""
import logging
from datetime import datetime

from telethon import events, functions, types

from selfbot.config import config

log = logging.getLogger("selfbot.saver")


def register(client) -> None:
    if not config.ENABLE_TIMED_SAVER:
        log.info("Timed media saver disabled.")
        return

    @client.on(events.NewMessage(incoming=True))
    async def on_timed_media(event: events.NewMessage.Event) -> None:
        msg = event.message
        media = msg.media
        if not isinstance(media, (types.MessageMediaPhoto, types.MessageMediaDocument)):
            return

        # Only handle media that is marked as self-destructing.
        is_ttl = bool(getattr(media, "ttl_seconds", None))
        if not is_ttl:
            return

        try:
            # Extend the timer so we have time to screenshot it.
            await client(functions.messages.GetMessagesRequest(id=[msg.id]))

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = ".jpg" if isinstance(media, types.MessageMediaPhoto) else ".mp4"
            out = config.DOWNLOAD_DIR / f"timed_{msg.sender_id}_{stamp}{ext}"

            data = await client.download_media(msg, file=bytes)
            if data:
                out.write_bytes(data)
                log.info("Saved timed media -> %s", out)
                await client.send_message("me", f"📸 Saved timed media: `{out.name}`")
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not save timed media: %s", exc)
