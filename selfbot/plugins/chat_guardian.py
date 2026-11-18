"""Chat Guardian: saves deleted / self-destructing / edited private messages to Saved Messages.

Per-user toggles are read from DB (g_deleted, g_selfdestruct, g_edited).
Only handles PRIVATE chats from real users (not bots/groups).
"""
import logging
from datetime import datetime

from telethon import events

from selfbot.config import config

log = logging.getLogger("selfbot.guardian")

SIGNATURE = "🛡 Jesus Self | نگهبان چت"
_MSG_CACHE = {}
_CACHE_MAX = 500


def _fmt_dt(dt) -> str:
    try:
        import pytz
        tz = pytz.timezone("Asia/Tehran")
        if dt.tzinfo is None:
            import datetime as _dtmod
            dt = dt.replace(tzinfo=_dtmod.timezone.utc)
        return dt.astimezone(tz).strftime("%Y/%m/%d %H:%M")
    except Exception:
        try:
            import pytz
            return datetime.now(pytz.timezone("Asia/Tehran")).strftime("%Y/%m/%d %H:%M")
        except Exception:
            return datetime.now().strftime("%Y/%m/%d %H:%M")


def _cache_put(chat_id, msg_id, data):
    # Only cache PRIVATE chats (positive user IDs, not groups/channels with negative IDs)
    try:
        cid = int(chat_id)
    except Exception:
        return
    if cid < 0:
        return
    _MSG_CACHE[(chat_id, msg_id)] = data
    if len(_MSG_CACHE) > _CACHE_MAX:
        for k in list(_MSG_CACHE.keys())[:100]:
            _MSG_CACHE.pop(k, None)


def register(client) -> None:
    _me_id = {"v": None}

    async def _flags():
        if _me_id["v"] is None:
            try:
                me = await client.get_me()
                _me_id["v"] = me.id
            except Exception:
                return {}
        try:
            from bot.database import get_feature_flags
            return await get_feature_flags(_me_id["v"])
        except Exception:
            return {}

    @client.on(events.NewMessage(incoming=True))
    async def _on_new(event: events.NewMessage.Event) -> None:
        if not event.is_private:
            return
        try:
            if int(event.chat_id) < 0:
                return
        except Exception:
            return
        try:
            sender = await event.get_sender()
            if getattr(sender, "bot", False):
                return
        except Exception:
            pass
        msg = event.message
        try:
            sender = await msg.get_sender()
            name = getattr(sender, "first_name", None) or "نامشخص"
            _cache_put(event.chat_id, msg.id, {
                "text": msg.raw_text or "",
                "sender_id": msg.sender_id,
                "sender_name": name,
                "date": msg.date,
                "has_media": bool(msg.media),
            })
        except Exception:
            pass

        if not msg.media:
            return
        flags = await _flags()
        if not flags.get("g_selfdestruct", True):
            return
        is_ttl = bool(getattr(msg.media, "ttl_seconds", None))
        if not is_ttl:
            return
        try:
            data = await client.download_media(msg, file=bytes)
            if not data:
                return
            name = "نامشخص"
            try:
                snd = await msg.get_sender()
                name = getattr(snd, "first_name", None) or "نامشخص"
            except Exception:
                pass
            caption = (
                f"💥 <b>مدیای نابود شونده ذخیره شد</b>\n\n"
                f"<blockquote>این رسانه پس از مشاهده نابود می‌شد و اکنون در امان است.</blockquote>\n\n"
                f"👤 <b>از:</b> {name} (<code>{msg.sender_id}</code>)\n"
                f"📅 <b>تاریخ:</b> {_fmt_dt(msg.date)}\n\n"
                f"{SIGNATURE}"
            )
            await client.send_file("me", data, caption=caption, parse_mode="html")
            log.info("Saved self-destructing media from %s", msg.sender_id)
        except Exception as e:
            log.warning(f"selfdestruct save failed: {e}")

    @client.on(events.MessageEdited(incoming=True))
    async def _on_edited(event: events.MessageEdited.Event) -> None:
        if not event.is_private:
            return
        try:
            sender = await event.get_sender()
            if getattr(sender, "bot", False):
                return
        except Exception:
            pass
        flags = await _flags()
        if not flags.get("g_edited", True):
            return
        msg = event.message
        cached = _MSG_CACHE.get((event.chat_id, msg.id))
        old_text = cached["text"] if cached else "(نامشخص)"
        new_text = msg.raw_text or ""
        # Skip false-positive edits: if text is unchanged, do nothing
        if cached and (cached.get("text") or "") == new_text:
            return
        try:
            sender = await msg.get_sender()
            name = getattr(sender, "first_name", None) or "نامشخص"
        except Exception:
            name = "نامشخص"
        body = (
            f"✏️ <b>پیام ویرایش شد</b>\n\n"
            f"<blockquote><b>Original:</b>\n{old_text}</blockquote>\n\n"
            f"<blockquote><b>Edited:</b>\n{new_text}</blockquote>\n\n"
            f"👤 <b>از:</b> {name} (<code>{msg.sender_id}</code>)\n"
            f"📅 <b>تاریخ:</b> {_fmt_dt(msg.date)}\n\n"
            f"{SIGNATURE}"
        )
        try:
            await client.send_message("me", body, parse_mode="html")
            if cached:
                cached["text"] = new_text
                _MSG_CACHE[(event.chat_id, msg.id)] = cached
        except Exception as e:
            log.warning(f"edited save failed: {e}")

    @client.on(events.MessageDeleted())
    async def _on_deleted(event: events.MessageDeleted.Event) -> None:
        ids = list(event.deleted_ids or [])
        if not ids and getattr(event, "deleted_id", None):
            ids = [event.deleted_id]
        # event.chat_id can be None for private-chat deletions; try to recover it from cache
        try:
            cid = int(event.chat_id) if event.chat_id is not None else None
        except Exception:
            cid = None
        if cid is not None and cid < 0:
            return
        for msg_id in ids:
            cached = None
            if cid is not None:
                cached = _MSG_CACHE.pop((cid, msg_id), None)
            if not cached:
                # Fallback: match by message_id only; cached entries are already private-only
                for k in list(_MSG_CACHE.keys()):
                    if k[1] == msg_id:
                        cached = _MSG_CACHE.pop(k, None)
                        break
            if not cached:
                continue
            if not cached:
                continue
            flags = await _flags()
            if not flags.get("g_deleted", True):
                continue
            text = cached["text"] or ""
            if not text and not cached["has_media"]:
                continue
            body = (
                f"🗑 <b>پیام حذف شد</b>\n\n"
                f"<blockquote>{text if text else '(فقط رسانه بود)'}</blockquote>\n\n"
                f"👤 <b>از:</b> {cached['sender_name']} (<code>{cached['sender_id']}</code>)\n"
                f"📅 <b>تاریخ:</b> {_fmt_dt(cached['date'])}\n\n"
                f"{SIGNATURE}"
            )
            try:
                await client.send_message("me", body, parse_mode="html")
                log.info("Saved deleted message from %s", cached['sender_id'])
            except Exception as e:
                log.warning(f"deleted save failed: {e}")
