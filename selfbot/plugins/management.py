"""Management plugin:
- `.حذف` (reply) → delete message both sides
- `.حذف N` (1..100) → delete last N messages (current topic in forum groups)
- `.سکوت` (reply/in PV) → mute a user in PV: their messages get deleted instantly
- `.قفل پیوی` → toggle PV lock: any incoming PV gets deleted instantly
- `.منشی روشن|خاموش` → auto-reply secretary on/off
- `.تنظیم متن منشی <text>` → set secretary text
- `.اسپم <text> <N>` → send text N times (1..100)
All settings are per-user and stored in Neon.
"""
import asyncio
import logging
from telethon import events
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator

from selfbot.config import config

log = logging.getLogger("selfbot.management")
SIG = "🛡 Jesus Self | مدیریت"


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

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{re.escape(p)}حذف(?:\s+(\d+))?$"))
    async def cmd_delete(event: events.NewMessage.Event) -> None:
        m = event.pattern_match
        n = m.group(1)
        try:
            if n:
                cnt = max(1, min(100, int(n)))
                ids = []
                async for msg in client.iter_messages(event.chat_id, limit=cnt):
                    # In forum topics, only delete within the current topic
                    if getattr(event.message, "reply_to", None) and getattr(event.message.reply_to, "forum_topic", False):
                        topic_id = event.message.reply_to.reply_to_top_id or event.message.reply_to.reply_to_msg_id
                        if getattr(msg, "reply_to", None) and getattr(msg.reply_to, "reply_to_top_id", None) != topic_id and getattr(msg.reply_to, "reply_to_msg_id", None) != topic_id:
                            continue
                    ids.append(msg.id)
                if ids:
                    await client.delete_messages(event.chat_id, ids)
                return
            if not event.is_reply:
                await event.edit(f"❌ روی پیام موردنظر ریپلای کن و بزن <code>{p}حذف</code> یا <code>{p}حذف 100</code>", parse_mode="html")
                return
            replied = await event.get_reply_message()
            await client.delete_messages(event.chat_id, [replied.id, event.id])
        except Exception as e:
            try:
                await event.edit(f"❌ حذف نشد: <code>{e}</code>", parse_mode="html")
            except Exception:
                pass

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{re.escape(p)}سکوت$"))
    async def cmd_mute(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        if not event.is_reply:
            await event.edit(f"❌ روی پیام کاربر ریپلای کن و بزن <code>{p}سکوت</code>", parse_mode="html")
            return
        try:
            replied = await event.get_reply_message()
            target = replied.sender_id
            if not target or target == uid:
                await event.edit("❌ کاربر نامعتبر.")
                return
            from bot.database import add_muted
            await add_muted(uid, target)
            name = "کاربر"
            try:
                s = await replied.get_sender()
                name = getattr(s, "first_name", None) or name
            except Exception:
                pass
            await event.edit(
                f"🔇 کاربر <b>{name}</b> (<code>{target}</code>) سکوت شد.\n"
                f"<blockquote>از این به بعد هر پیامی بفرستد فوراً حذف می‌شود.</blockquote>\n\n{SIG}",
                parse_mode="html",
            )
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{re.escape(p)}قفل پیوی$"))
    async def cmd_lock_pv(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        from bot.database import toggle_setting, get_setting
        try:
            new = await toggle_setting(uid, "lock_pv")
            st = "🟢 فعال" if new else "🔴 غیرفعال"
            await event.edit(f"🔒 <b>قفل پیوی:</b> {st}\n\n{SIG}", parse_mode="html")
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{re.escape(p)}منشی\s+(روشن|خاموش)$"))
    async def cmd_secretary(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        state = event.pattern_match.group(1)
        from bot.database import set_setting, get_setting
        on = 1 if state == "روشن" else 0
        if on and not await get_setting(uid, "secretary_text"):
            await event.edit(f"⚠️ اول متن منشی را تنظیم کن: <code>{p}تنظیم متن منشی [متن]</code>", parse_mode="html")
            return
        await set_setting(uid, "secretary_on", on)
        await event.edit(f"🤖 <b>منشی:</b> {'🟢 روشن' if on else '🔴 خاموش'}\n\n{SIG}", parse_mode="html")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{re.escape(p)}تنظیم متن منشی (.+)$"))
    async def cmd_set_secretary_text(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        text = event.pattern_match.group(1).strip()
        if not text:
            return
        from bot.database import set_setting
        await set_setting(uid, "secretary_text", text)
        await event.edit(
            f"✅ متن منشی تنظیم شد:\n<blockquote>{text}</blockquote>\n\n{SIG}",
            parse_mode="html",
        )

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{re.escape(p)}اسپم (.+?)(?:\s+(\d+))?$"))
    async def cmd_spam(event: events.NewMessage.Event) -> None:
        text = event.pattern_match.group(1).strip()
        n_str = event.pattern_match.group(2)
        n = 5 if not n_str else max(1, min(100, int(n_str)))
        # Strip trailing number from text if pattern greedy
        if not text:
            return
        chat_id = event.chat_id
        try:
            await event.delete()
        except Exception:
            pass
        sent = 0
        for _ in range(n):
            try:
                await client.send_message(chat_id, text)
                sent += 1
                await asyncio.sleep(0.15)
            except Exception as e:
                log.warning(f"spam error: {e}")
                break
        try:
            await client.send_message(chat_id, f"✅ اسپم با موفقیت به پایان رسید ({sent}/{n}) — {SIG}")
        except Exception:
            pass

    # --- Incoming enforcement: muted users, PV lock, secretary ---
    @client.on(events.NewMessage(incoming=True))
    async def on_incoming(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        if not uid:
            return
        sender = event.sender_id
        if not sender or sender == uid:
            return
        try:
            from bot.database import is_muted, get_setting
            # 1) muted users in PV: delete instantly
            if event.is_private and await is_muted(uid, sender):
                try:
                    await event.delete()
                except Exception:
                    pass
                return
            # 2) PV lock: delete any incoming PV from non-contacts
            if event.is_private and await get_setting(uid, "lock_pv", 0):
                try:
                    await event.delete()
                except Exception:
                    pass
                return
            # 3) Secretary auto-reply in PV
            if event.is_private and await get_setting(uid, "secretary_on", 0):
                txt = await get_setting(uid, "secretary_text")
                if txt:
                    try:
                        await event.reply(txt)
                    except Exception:
                        pass
        except Exception as e:
            log.warning(f"incoming enforcement failed: {e}")
