"""Enemies plugin.

- `.تنظیم دشمن` (reply to a user) → adds that user to your enemy list.
- `.افزودن فحش <text>` → adds a custom curse to your curse pool.
- On every message from an enemy (in private or group), replies with a random curse from the pool.
Per-user: each user has their own enemy list and curse list.
"""
import random
import logging
from telethon import events

from selfbot.config import config

log = logging.getLogger("selfbot.enemies")

SIGNATURE = "🛡 Jesus Self | دشمنان"


def register(client) -> None:
    p = config.PREFIX
    _me_id = {"v": None}

    async def _own_id():
        if _me_id["v"] is None:
            try:
                me = await client.get_me()
                _me_id["v"] = me.id
            except Exception:
                pass
        return _me_id["v"]

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}تنظیم دشمن(?:\s+(.+))?$"))
    async def set_enemy(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        if not uid:
            return
        arg = (event.pattern_match.group(1) or "").strip()
        target = None
        tname = "نامشخص"
        try:
            if event.is_reply:
                replied = await event.get_reply_message()
                target = replied.sender_id
                try:
                    tsender = await replied.get_sender()
                    tname = getattr(tsender, "first_name", None) or "نامشخص"
                except Exception:
                    pass
            elif arg:
                # Try numeric ID first
                cleaned = arg.lstrip("@")
                if cleaned.lstrip("-").isdigit():
                    target = int(cleaned)
                else:
                    try:
                        ent = await client.get_entity(cleaned)
                        target = ent.id
                        tname = getattr(ent, "first_name", None) or getattr(ent, "title", None) or cleaned
                    except Exception:
                        await event.edit(f"❌ کاربر <code>{arg}</code> پیدا نشد.", parse_mode="html")
                        return
            else:
                await event.edit("❌ یا روی پیام شخص ریپلای کن، یا یوزرنیم/آیدی عددی بده: <code>.تنظیم دشمن @username</code>", parse_mode="html")
                return
            if not target:
                await event.edit("❌ نتوانستم کاربر هدف را تشخیص بدهم.")
                return
            if target == uid:
                await event.edit("😅 نمی‌تونی خودت رو دشمن کنی!")
                return
            from bot.database import add_enemy
            await add_enemy(uid, target, tname)
            await event.edit(
                f"☠️ <b>{tname}</b> (<code>{target}</code>) به لیست دشمنان اضافه شد.\n\n"
                f"{SIGNATURE}",
                parse_mode="html",
            )
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}حذف دشمن(?:\s+(.+))?$"))
    async def remove_enemy_cmd(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        if not uid:
            return
        arg = (event.pattern_match.group(1) or "").strip()
        target = None
        tname = "نامشخص"
        try:
            if event.is_reply:
                replied = await event.get_reply_message()
                target = replied.sender_id
                try:
                    tsender = await replied.get_sender()
                    tname = getattr(tsender, "first_name", None) or "نامشخص"
                except Exception:
                    pass
            elif arg:
                cleaned = arg.lstrip("@")
                if cleaned.lstrip("-").isdigit():
                    target = int(cleaned)
                else:
                    try:
                        ent = await client.get_entity(cleaned)
                        target = ent.id
                        tname = getattr(ent, "first_name", None) or cleaned
                    except Exception:
                        await event.edit(f"❌ کاربر <code>{arg}</code> پیدا نشد.", parse_mode="html")
                        return
            else:
                await event.edit("❌ روی پیام شخص ریپلای کن، یا یوزرنیم/آیدی بده: <code>.حذف دشمن @username</code>", parse_mode="html")
                return
            if not target:
                await event.edit("❌ نتوانستم کاربر هدف را تشخیص بدهم.")
                return
            from bot.database import remove_enemy, get_enemies
            if not tname or tname == "نامشخص":
                for e in await get_enemies(uid):
                    if e["enemy_id"] == target:
                        tname = e["enemy_name"] or tname
                        break
            await remove_enemy(uid, target)
            await event.edit(
                f"✅ <b>{tname}</b> (<code>{target}</code>) از لیست دشمنان حذف شد.\n\n{SIGNATURE}",
                parse_mode="html",
            )
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}پاکسازی لیست فحش$"))
    async def clear_curses_cmd(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        if not uid:
            return
        try:
            from bot.database import clear_curses
            await clear_curses(uid)
            await event.edit(f"🧹 تمام فحش‌های شما از لیست پاک شد.\n\n{SIGNATURE}", parse_mode="html")
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}افزودن فحش (.+)$"))
    async def add_curse(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        if not uid:
            return
        text = event.pattern_match.group(1).strip()
        if not text:
            return
        from bot.database import add_curse
        try:
            await add_curse(uid, text)
            await event.edit(
                f"✅ فحش به لیست شما اضافه شد:\n<blockquote>{text}</blockquote>\n\n{SIGNATURE}",
                parse_mode="html",
            )
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")

    @client.on(events.NewMessage(incoming=True))
    async def on_enemy_msg(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        if not uid:
            return
        sender_id = event.sender_id
        if not sender_id or sender_id == uid:
            return
        try:
            from bot.database import is_enemy, get_curses
            if not await is_enemy(uid, sender_id):
                return
            curses = await get_curses(uid)
            if not curses:
                return
            curse = random.choice(curses)
        except Exception as e:
            log.warning(f"enemy check failed: {e}")
            return
        try:
            await event.reply(curse)
        except Exception as e:
            log.warning(f"enemy reply failed: {e}")
