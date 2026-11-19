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
    import re as _re
    p = config.PREFIX
    _ep = _re.escape(p)
    _me = {"id": None}

    async def _own_id():
        if _me["id"] is None:
            try:
                if not client.is_connected():
                    return None
                me = await client.get_me()
                _me["id"] = me.id
            except Exception:
                pass
        return _me["id"]

    async def _get(col, default=0):
        uid = await _own_id()
        if not uid:
            return default
        try:
            from bot.database import get_setting
            return await get_setting(uid, col, default)
        except Exception:
            return default

    async def _toggle(col):
        uid = await _own_id()
        from bot.database import toggle_setting
        return await toggle_setting(uid, col)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{_ep}همیشه انلاین$"))
    async def cmd_always_online(event: events.NewMessage.Event) -> None:
        try:
            new = await _toggle("always_online")
            await event.edit(f"🟢 <b>همیشه آنلاین:</b> {'روشن' if new else 'خاموش'}\n\n{SIG}", parse_mode="html")
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{_ep}همیشه در حال نوشتن$"))
    async def cmd_always_typing(event: events.NewMessage.Event) -> None:
        try:
            new = await _toggle("always_typing")
            await event.edit(f"✍️ <b>همیشه در حال نوشتن:</b> {'روشن' if new else 'خاموش'}\n\n{SIG}", parse_mode="html")
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")



    async def _online_loop():
        """Hammer UpdateStatus every 8s so the account never goes offline."""
        while True:
            try:
                if await _get("always_online"):
                    try:
                        await client(functions.account.UpdateStatusRequest(offline=False))
                    except Exception:
                        pass
            except Exception:
                pass
            await asyncio.sleep(8)

    async def _typing_loop():
        """Continuously broadcast typing to all group dialogs."""
        while True:
            try:
                if await _get("always_typing"):
                    # Collect target chats once per cycle
                    targets = []
                    async for dialog in client.iter_dialogs(limit=25):
                        if dialog.is_group or dialog.is_channel:
                            targets.append(dialog.id)
                    for tid in targets:
                        try:
                            await client(functions.messages.SetTypingRequest(peer=tid, action=SendMessageTypingAction()))
                        except Exception:
                            pass
                        await asyncio.sleep(0.3)
            except Exception:
                pass
            await asyncio.sleep(20)

    asyncio.create_task(_online_loop())
    asyncio.create_task(_typing_loop())
