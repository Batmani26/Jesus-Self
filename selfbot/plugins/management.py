"""Management plugin (fixed regex + topic-aware delete + proper mute/lock/secretary/spam)."""
import asyncio
import logging
from telethon import events

from selfbot.config import config

log = logging.getLogger("selfbot.management")
SIG = "🛡 Jesus Self | مدیریت"


def register(client) -> None:
    p = config.PREFIX
    ep = __import__("re").escape(p)
    _me = {"id": None}

    async def _own_id():
        if _me["id"] is None:
            try:
                me = await client.get_me()
                _me["id"] = me.id
            except Exception:
                pass
        return _me["id"]

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{ep}حذف(?:\s+(\d+))?$"))
    async def cmd_delete(event: events.NewMessage.Event) -> None:
        m = event.pattern_match
        n = m.group(1)
        chat_id = event.chat_id
        try:
            # Determine topic id (if inside a forum topic, not the main topic)
            topic_id = None
            rt = getattr(event.message, "reply_to", None)
            if rt is not None:
                if getattr(rt, "forum_topic", False):
                    topic_id = getattr(rt, "reply_to_top_id", None) or getattr(rt, "reply_to_msg_id", None)
            try:
                await event.delete()
            except Exception:
                pass

            if n:
                cnt = max(1, min(100, int(n)))
                ids = []
                kw = {}
                if topic_id:
                    kw["reply_to"] = topic_id
                async for msg in client.iter_messages(chat_id, limit=cnt, **kw):
                    ids.append(msg.id)
                if ids:
                    await client.delete_messages(chat_id, ids, revoke=True)
                try:
                    done = await client.send_message(
                        chat_id,
                        f"🧹 <b>پاکسازی با موفقیت انجام شد</b> ({len(ids)} پیام)\n\n{SIG}",
                        parse_mode="html",
                        reply_to=topic_id if topic_id else None,
                    )
                except Exception:
                    pass
                return

            if not event.is_reply:
                await client.send_message(
                    chat_id,
                    f"❌ روی یک پیام ریپلای کن و <code>{p}حذف</code> بزن، یا بنویس <code>{p}حذف 100</code>",
                    parse_mode="html",
                )
                return
            replied = await event.get_reply_message()
            if replied:
                await client.delete_messages(chat_id, [replied.id, event.id], revoke=True)
        except Exception as e:
            log.warning(f"delete failed: {e}")
            try:
                await client.send_message(chat_id, f"❌ حذف نشد: <code>{e}</code>", parse_mode="html")
            except Exception:
                pass

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{ep}سکوت$"))
    async def cmd_mute(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        if not event.is_reply:
            await event.edit(f"❌ روی پیام کاربر ریپلای کن و <code>{p}سکوت</code> بزن.", parse_mode="html")
            return
        try:
            replied = await event.get_reply_message()
            target = replied.sender_id
            if not target or target == uid:
                await event.edit("❌ کاربر نامعتبر.")
                return
            name = "کاربر"
            try:
                s = await replied.get_sender()
                name = getattr(s, "first_name", None) or getattr(s, "title", None) or name
            except Exception:
                pass
            # In groups, verify we have admin rights to delete
            if not event.is_private:
                try:
                    perms = await client.get_permissions(event.chat_id, uid)
                    if not (getattr(perms, "delete_messages", False) or getattr(perms, "is_admin", False) or getattr(perms, "is_creator", False)):
                        await event.edit("⛔ شما دسترسی مورد نیاز (حذف پیام) را ندارید.")
                        return
                except Exception:
                    pass
            from bot.database import add_muted
            await add_muted(uid, target)
            await event.edit(
                f"🔇 <b>کاربر {name}</b> (<code>{target}</code>) با موفقیت سکوت شد.\n\n"
                f"<blockquote>از این به بعد پیام‌هایش فوراً حذف می‌شوند.</blockquote>\n\n{SIG}",
                parse_mode="html",
            )
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{ep}حذف سکوت$"))
    async def cmd_unmute(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        if not event.is_reply:
            await event.edit(f"❌ روی پیام کاربر سکوت‌شده ریپلای کن و <code>{p}حذف سکوت</code> بزن.", parse_mode="html")
            return
        try:
            replied = await event.get_reply_message()
            target = replied.sender_id
            if not target or target == uid:
                await event.edit("❌ کاربر نامعتبر.")
                return
            name = "کاربر"
            try:
                s = await replied.get_sender()
                name = getattr(s, "first_name", None) or getattr(s, "title", None) or name
            except Exception:
                pass
            from bot.database import remove_muted
            await remove_muted(uid, target)
            await event.edit(
                f"🔊 <b>کاربر {name}</b> (<code>{target}</code>) از سکوت خارج شد.\n\n"
                f"<blockquote>از این به بعد پیام‌هایش حذف نمی‌شوند.</blockquote>\n\n{SIG}",
                parse_mode="html",
            )
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{ep}بازکردن قفل پیوی$"))
    async def cmd_unlock_pv(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        from bot.database import set_setting
        try:
            await set_setting(uid, "lock_pv", 0)
            await event.edit(
                f"🔓 <b>قفل پیوی:</b> 🔴 غیرفعال (باز شد)\n\n"
                f"<blockquote>از این به بعد پیام‌های ورودی در پیوی حذف نمی‌شوند.</blockquote>\n\n{SIG}",
                parse_mode="html",
            )
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{ep}قفل پیوی$"))
    async def cmd_lock_pv(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        from bot.database import toggle_setting
        try:
            new = await toggle_setting(uid, "lock_pv")
            st = "🟢 فعال" if new else "🔴 غیرفعال"
            await event.edit(
                f"🔒 <b>قفل پیوی:</b> {st}\n\n"
                f"<blockquote>وضعیت قفل پیوی شما اکنون {'فعال است — پیام‌های ورودی حذف می‌شوند' if new else 'غیرفعال است'}.</blockquote>\n\n{SIG}",
                parse_mode="html",
            )
        except Exception as e:
            await event.edit(f"❌ خطا: <code>{e}</code>", parse_mode="html")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{ep}منشی\s+(روشن|خاموش)$"))
    async def cmd_secretary(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        state = event.pattern_match.group(1)
        from bot.database import set_setting, get_setting
        on = 1 if state == "روشن" else 0
        txt = await get_setting(uid, "secretary_text")
        if on and not txt:
            await event.edit(f"⚠️ اول متن منشی را تنظیم کن: <code>{p}تنظیم متن منشی [متن]</code>", parse_mode="html")
            return
        await set_setting(uid, "secretary_on", on)
        tail = f"\n\n<blockquote>متن فعلی منشی:\n{txt}</blockquote>" if txt else ""
        await event.edit(
            f"🤖 <b>منشی:</b> {'🟢 روشن' if on else '🔴 خاموش'}{tail}\n\n{SIG}",
            parse_mode="html",
        )

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{ep}تنظیم متن منشی (.+)$"))
    async def cmd_set_secretary_text(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        text = event.pattern_match.group(1).strip()
        if not text:
            return
        from bot.database import set_setting
        await set_setting(uid, "secretary_text", text)
        await event.edit(
            f"✅ متن منشی با موفقیت تنظیم شد:\n<blockquote>{text}</blockquote>\n\n{SIG}",
            parse_mode="html",
        )

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{ep}اسپم\s+(.+?)(?:\s+(\d+))?$"))
    async def cmd_spam(event: events.NewMessage.Event) -> None:
        raw = event.pattern_match.group(1).strip()
        n_str = event.pattern_match.group(2)
        n = 5 if not n_str else max(1, min(100, int(n_str)))
        # If pattern didn't capture trailing number cleanly, split last token
        if not n_str:
            parts = raw.rsplit(" ", 1)
            if len(parts) == 2 and parts[1].isdigit():
                raw = parts[0]
                n = max(1, min(100, int(parts[1])))
        text = raw.strip()
        if not text:
            return
        chat_id = event.chat_id
        try:
            await event.delete()
        except Exception:
            pass
        try:
            await client.send_message(chat_id, f"💥 اسپم آغاز شد ({n} بار) — {SIG}")
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
            if event.is_private and await is_muted(uid, sender):
                try:
                    await event.delete()
                except Exception:
                    pass
                return
            if event.is_private and await get_setting(uid, "lock_pv", 0):
                try:
                    await event.delete()
                except Exception:
                    pass
                return
            if event.is_private and await get_setting(uid, "secretary_on", 0):
                txt = await get_setting(uid, "secretary_text")
                if txt:
                    try:
                        await event.reply(txt)
                    except Exception:
                        pass
        except Exception as e:
            log.warning(f"incoming enforcement failed: {e}")
