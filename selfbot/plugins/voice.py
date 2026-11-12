"""Text-to-voice plugin: `.say <text>` converts text into a voice message."""
import logging
import tempfile

from telethon import events

from selfbot.config import config

log = logging.getLogger("selfbot.voice")


def register(client) -> None:
    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{config.PREFIX}say (.+)$"))
    async def say_cmd(event: events.NewMessage.Event) -> None:
        text = event.pattern_match.group(1).strip()
        if not text:
            return
        try:
            from gtts import gTTS
        except ImportError:
            await event.edit("❌ `gTTS` is not installed. Run: `pip install gTTS`")
            return

        await event.edit("🎙 Generating voice...")
        try:
            tts = gTTS(text=text, lang="fa")
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tts.save(tmp.name)
            await event.client.send_file(
                event.chat_id,
                tmp.name,
                voice_note=True,
                reply_to=event.reply_to_msg_id,
            )
            await event.delete()
        except Exception as exc:  # noqa: BLE001
            log.exception("TTS failed: %s", exc)
            await event.edit(f"❌ TTS failed: `{exc}`")
