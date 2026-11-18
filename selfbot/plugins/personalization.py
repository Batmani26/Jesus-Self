"""Personalization plugin: always online, always typing, auto-seen.
Toggles are stored per-user in Neon (always_online, always_typing, auto_seen).
"""
import asyncio
import logging
from telethon import events, functions
from telethon.tl.types import SendMessageTypingAction

from selfbot.config import config

log = logging.getLogger("selfbot.personalization")
SIG = "🛡 Jesus Self | شخصی‌سازی"


def register(client) -> None:
    p = config.PREFIX
    _me = {"id": None}

    async def _own_id():
        if _me["id"] is None:
            try:
                me = await client.get_me()
                _me["id"] = me.id
            except Exception:
                pass
        return _me["id"]

    async def _get(col, default=0):
        uid = await _own_id()
        try:
            from bot.database import get_setting
            return await get_setting(uid, col, default)
        except Exception:
            return default

    async def _toggle(col):
        uid = await _own_id()
        from bot.database import toggle_setting
        return await toggle_setting(uid, col)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{re.escape(p)}همیشه انلاین$"))
    async def cmd_always_online(event: events.NewMessage.Event) -> None:
        try:
            new = await _toggle("always_online")
            await event.edit(f"🟢 <b>همیشه آنلاین:</b> {'روشن' if new else 'خاموش'}\n\n{SIG}", parse_mode="html")
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{re.escape(p)}همیشه در حال نوشتن$"))
    async def cmd_always_typing(event: events.NewMessage.Event) -> None:
        try:
            new = await _toggle("always_typing")
            await event.edit(f"✍️ <b>همیشه در حال نوشتن:</b> {'روشن' if new else 'خاموش'}\n\n{SIG}", parse_mode="html")
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{re.escape(p)}سین خودکار$"))
    async def cmd_auto_seen(event: events.NewMessage.Event) -> None:
        try:
            new = await _toggle("auto_seen")
            await event.edit(f"👁 <b>سین خودکار:</b> {'روشن' if new else 'خاموش'}\n\n{SIG}", parse_mode="html")
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")

    async def _online_loop():
        while True:
            try:
                if await _get("always_online"):
                    await client(functions.account.UpdateStatusRequest(offline=False))
            except Exception:
                pass
            await asyncio.sleep(25)

    async def _typing_loop():
        while True:
            try:
                if await _get("always_typing"):
                    async for dialog in client.iter_dialogs(limit=15):
                        if dialog.is_group or dialog.is_channel:
                            try:
                                await client(functions.messages.SetTypingRequest(peer=dialog.id, action=SendMessageTypingAction()))
                            except Exception:
                                pass
                            await asyncio.sleep(0.5)
            except Exception:
                pass
            await asyncio.sleep(45)

    async def _seen_loop():
        while True:
            try:
                if await _get("auto_seen"):
                    async for dialog in client.iter_dialogs(limit=20):
                        try:
                            await client.send_read_acknowledge(dialog.id)
                        except Exception:
                            pass
                        await asyncio.sleep(0.3)
            except Exception:
                pass
            await asyncio.sleep(30)

    asyncio.create_task(_online_loop())
    asyncio.create_task(_typing_loop())
    asyncio.create_task(_seen_loop())
