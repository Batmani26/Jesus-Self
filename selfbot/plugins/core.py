"""Core commands: .help, .ping, .info."""
import platform
import time

from telethon import events

from selfbot import __version__
from selfbot.config import config


HELP_TEXT = """🤖 **Jesus Self — Commands**

• `.help` — this menu
• `.ping` — latency check
• `.info` — account & version info
• `.say <text>` — text ➜ voice 🎙
• `.song <name>` — search & send music 🎵
• `.ad <text>` — broadcast an ad to chats 📢

**Auto features:**
• 📸 Timed photo/video saver (DM)
"""


def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}help$"))
    async def help_cmd(event: events.NewMessage.Event) -> None:
        await event.edit(HELP_TEXT)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}ping$"))
    async def ping_cmd(event: events.NewMessage.Event) -> None:
        start = time.perf_counter()
        await event.edit("🏓 Pong...")
        ms = (time.perf_counter() - start) * 1000
        await event.edit(f"🏓 **Pong!** `{ms:.0f} ms`")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}info$"))
    async def info_cmd(event: events.NewMessage.Event) -> None:
        me = await event.client.get_me()
        text = (
            f"👤 **{me.first_name}** (@{me.username or '-'})\n"
            f"🆔 `{me.id}`\n"
            f"📦 Jesus Self `v{__version__}`\n"
            f"🖥 `{platform.system()} {platform.release()}`"
        )
        await event.edit(text)
