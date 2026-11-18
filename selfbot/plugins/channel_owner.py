"""Channel Owner resolver.

Command:
  `.مالک <link|@username|id>`
Resolves a channel / supergroup / group to its creator (owner) using Telegram's own data.
"""
import logging
import re
from telethon import events
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import ChannelParticipantsAdmins, Channel, Chat

from selfbot.config import config

log = logging.getLogger("selfbot.channel_owner")
SIG = "🛡 Jesus Self | مالک کانال"


async def _resolve_entity(client, raw: str):
    raw = raw.strip()
    # Numeric id (possibly negative)
    if re.fullmatch(r"-?\d+", raw):
        try:
            return await client.get_entity(int(raw))
        except Exception:
            pass
    # @username or t.me link
    m = re.search(r"(?:t\.me/|telegram\.me/)(?:\+|joinchat/)?([A-Za-z0-9_\-]+)", raw)
    if m:
        name = m.group(1)
        if name.startswith("+"):
            # private invite link
            try:
                from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
                inv = await client(CheckChatInviteRequest(name.lstrip("+")))
                if hasattr(inv, "chat"):
                    return inv.chat
                joined = await client(ImportChatInviteRequest(name.lstrip("+")))
                return joined.chats[0]
            except Exception:
                pass
        try:
            return await client.get_entity(name)
        except Exception:
            pass
    if raw.startswith("@"):
        try:
            return await client.get_entity(raw)
        except Exception:
            pass
    try:
        return await client.get_entity(raw)
    except Exception:
        return None


async def _find_owner(client, entity):
    """Return (owner_id, owner_name, kind) or None."""
    try:
        if isinstance(entity, Channel):
            full = await client(GetFullChannelRequest(entity))
            chat_full = full.full_chat
            # 1) creator id in full_chat (available for channels usually)
            creator = getattr(chat_full, "creator_id", None)
            if creator:
                try:
                    u = await client.get_entity(creator)
                    nm = " ".join(filter(None, [getattr(u, "first_name", None), getattr(u, "last_name", None)])) or getattr(u, "username", "")
                except Exception:
                    nm = ""
                return creator, nm, "channel"
            # 2) scan admins for creator
            try:
                async for p in client.iter_participants(entity, filter=ChannelParticipantsAdmins):
                    if getattr(p, "participant", None) is not None and p.participant.__class__.__name__ in ("ChannelParticipantCreator",):
                        try:
                            u = await client.get_entity(p.id)
                            nm = " ".join(filter(None, [getattr(u, "first_name", None), getattr(u, "last_name", None)])) or getattr(u, "username", "")
                        except Exception:
                            nm = ""
                        return p.id, nm, "channel"
            except Exception:
                pass
            # 3) fallback: first admin in list
            try:
                async for p in client.iter_participants(entity, filter=ChannelParticipantsAdmins, limit=5):
                    try:
                        u = await client.get_entity(p.id)
                        nm = " ".join(filter(None, [getattr(u, "first_name", None), getattr(u, "last_name", None)])) or getattr(u, "username", "")
                    except Exception:
                        nm = ""
                    return p.id, nm, "channel"
            except Exception:
                pass
            return None
        if isinstance(entity, Chat):
            full = await client(GetFullChatRequest(entity.id))
            chat_full = full.full_chat
            creator = getattr(chat_full, "creator", None)
            if creator:
                try:
                    u = await client.get_entity(creator)
                    nm = " ".join(filter(None, [getattr(u, "first_name", None), getattr(u, "last_name", None)])) or getattr(u, "username", "")
                except Exception:
                    nm = ""
                return creator, nm, "group"
            return None
    except Exception as e:
        log.warning(f"find_owner failed: {type(e).__name__} - {e}")
        return None
    return None


def register(client) -> None:
    import re as _re
    _ep = _re.escape(config.PREFIX)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{_ep}مالک(?:\s+(.+))?$"))
    async def cmd_owner(event: events.NewMessage.Event) -> None:
        raw = (event.pattern_match.group(1) or "").strip()
        if not raw and event.is_reply:
            try:
                replied = await event.get_reply_message()
                fwd = getattr(replied, "fwd_from", None)
                if fwd and getattr(fwd, "from_id", None):
                    raw = str(getattr(fwd.from_id, "channel_id", None) or getattr(fwd.from_id, "user_id", None) or "")
            except Exception:
                pass
        if not raw:
            await event.edit(
                f"❌ لینک یا یوزرنیم کانال را بده:\n<code>{config.PREFIX}مالک https://t.me/yourchannel</code>\n"
                f"یا <code>{config.PREFIX}مالک @yourchannel</code>",
                parse_mode="html",
            )
            return

        await event.edit("🔎 در حال استعلام از تلگرام...")
        entity = await _resolve_entity(client, raw)
        if not entity:
            await event.edit(f"❌ موجودیت پیدا نشد: <code>{raw}</code>", parse_mode="html")
            return
        title = getattr(entity, "title", None) or getattr(entity, "username", None) or raw
        uname = getattr(entity, "username", None)
        res = await _find_owner(client, entity)
        if not res:
            await event.edit(
                f"⚠️ مالک پیدا نشد برای <b>{title}</b>.\n\n"
                f"<blockquote>ممکن است اطلاعات مالک فقط برای اعضا یا ادمین‌های کانال قابل مشاهده باشد، یا سلف‌بات عضو آن کانال نباشد.</blockquote>\n\n{SIG}",
                parse_mode="html",
            )
            return
        oid, oname, kind = res
        uname_part = f"@{uname}" if uname else "—"
        body = (
            f"👑 <b>مالک پیدا شد</b>\n\n"
            f"📢 <b>کانال/گروه:</b> {title} ({uname_part})\n"
            f"🆔 <b>آیدی کانال:</b> <code>{getattr(entity, 'id', '?')}</code>\n"
            f"👤 <b>مالک:</b> {oname or 'نامشخص'}\n"
            f"🆔 <b>آیدی عددی مالک:</b> <code>{oid}</code>\n\n"
            f"{SIG}"
        )
        try:
            await event.edit(body, parse_mode="html")
        except Exception:
            await client.send_message("me", body, parse_mode="html")
