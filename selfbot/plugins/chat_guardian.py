"""Chat Guardian: saves deleted / self-destructing / edited messages to Saved Messages.

Features (toggle from the panel 'نگهبان چت'):
- deleted:      forward deleted private messages
- selfdestruct: save self-destructing media immediately
- edited:       save original + new text of edited messages
"""
import logging
from datetime import datetime

from telethon import events, types

from selfbot.config import config

log = logging.getLogger("selfbot.guardian")

SIGNATURE = "\n\n🛡 نگهبان چت | Jesus Self"
# Simple in-memory cache of recent incoming messages: {(chat_id, msg_id): {text, sender, date, media}}
_MSG_CACHE = {}
_CACHE_MAX = 500


def _toggle(key: str) -> bool:
    try:
        from bot.main import GUARDIAN
        return GUARDIAN.get(key, True)
    except Exception:
        return True


def _fmt_dt(dt) -> str:
    try:
        return dt.strftime("%Y/%m/%d %H:%M")
    except Exception:
        return datetime.now().strftime("%Y/%m/%d %H:%M")


def _cache_put(chat_id, msg_id, data):
    _MSG_CACHE[(chat_id, msg_id)] = data
    if len(_MSG_CACHE) > _CACHE_MAX:
        # drop oldest ~100
        for k in list(_MSG_CACHE.keys())[:100]:
            _MSG_CACHE.pop(k, None)


def register(client) -> None:
    @client.on(events.NewMessage(incoming=True))
    async def _cache_and_selfdestruct(event: events.NewMessage.Event) -> None:
        msg = event.message
        # cache for deleted-detection
        try:
            sender = await msg.get_sender()
            name = getattr(sender, "first_name", None) or getattr(sender, "title", None) or "نامشخص"
            _cache_put(event.chat_id, msg.id, {
                "text": msg.raw_text or "",
                "sender_id": msg.sender_id,
                "sender_name": name,
                "date": msg.date,
                "has_media": bool(msg.media),
            })
        except Exception:
            pass

        # self-destructing media
        if not msg.media:
            return
        if not _toggle("selfdestruct"):
            return
        is_ttl = bool(getattr(msg.media, "ttl_seconds", None))
        if not is_ttl:
            return
        try:
            data = await client.download_media(msg, file=bytes)
            if not data:
                return
            try:
                sender = await msg.get_sender()
                name = getattr(sender, "first_name", None) or "نامشخص"
            except Exception:
                name = "نامشخص"
            caption = (
                f"💥 **مدیای نابود شونده ذخیره شد**\n"
                f"👤 از: {name} (`{msg.sender_id}`)\n"
                f"📅 {_fmt_dt(msg.date)}" + SIGNATURE
            )
            await client.send_file("me", data, caption=caption)
            log.info("Saved self-destructing media from %s", msg.sender_id)
        except Exception as e:
            log.warning(f"selfdestruct save failed: {e}")

    @client.on(events.MessageEdited(incoming=True))
    async def _on_edited(event: events.MessageEdited.Event) -> None:
        if not _toggle("edited"):
            return
        # Only private chats from real users (not bots, not groups/channels)
        if not event.is_private:
            return
        try:
            sender = await event.get_sender()
            if getattr(sender, "bot", False):
                return
        except Exception:
            pass
        msg = event.message
        cached = _MSG_CACHE.get((event.chat_id, msg.id))
        old_text = cached["text"] if cached else "(نامشخص)"
        new_text = msg.raw_text or ""
        try:
            sender = await msg.get_sender()
            name = getattr(sender, "first_name", None) or "نامشخص"
        except Exception:
            name = "نامشخص"
        caption = (
            f"✏️ **پیام ویرایش شد**\n"
            f"👤 از: {name} (`{msg.sender_id}`)\n"
            f"📅 {_fmt_dt(msg.date)}\n\n"
            f"🔸 قبل:\n{old_text}\n\n"
            f"🔹 بعد:\n{new_text}" + SIGNATURE
        )
        try:
            await client.send_message("me", caption)
            # update cache
            if cached:
                cached["text"] = new_text
                _MSG_CACHE[(event.chat_id, msg.id)] = cached
        except Exception as e:
            log.warning(f"edited save failed: {e}")

    @client.on(events.MessageDeleted())
    async def _on_deleted(event: events.MessageDeleted.Event) -> None:
        if not _toggle("deleted"):
            return
        ids = list(event.deleted_ids or [])
        if not ids and getattr(event, "deleted_id", None):
            ids = [event.deleted_id]
        log.info(f"[guardian] deleted event chat={event.chat_id} ids={ids} cache_size={len(_MSG_CACHE)}")
        for msg_id in ids:
            # Try exact key first
            cached = _MSG_CACHE.pop((event.chat_id, msg_id), None)
            if not cached:
                # Fallback: scan cache for this msg_id in any chat (handles chat_id mismatch)
                for k in list(_MSG_CACHE.keys()):
                    if k[1] == msg_id:
                        cached = _MSG_CACHE.pop(k, None)
                        break
            if not cached:
                continue
            text = cached["text"] or ""
            if not text and not cached["has_media"]:
                continue
            sender_name = cached["sender_name"]
            sender_id = cached["sender_id"]
            when = _fmt_dt(cached["date"])
            body = (
                f"🗑 **پیام حذف شد**\n"
                f"👤 از: {sender_name} (`{sender_id}`)\n"
                f"📅 تاریخ پیام: {when}\n\n"
                f"📝 متن:\n{text if text else '(فقط رسانه بود)'}" + SIGNATURE
            )
            try:
                await client.send_message("me", body)
                log.info("Saved deleted message from %s", sender_id)
            except Exception as e:
                log.warning(f"deleted save failed: {e}")
