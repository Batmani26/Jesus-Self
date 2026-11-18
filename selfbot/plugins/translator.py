"""Translator:
- `.ترجمه` (reply or inline text) → auto-detect:
    English/Latin text → translate to Persian
    Persian text      → translate to English
Edits the user's own message in-place (no extra message).
"""
import re
from telethon import events

from selfbot.config import config

_PERSIAN = re.compile(r"[\u0600-\u06FF]")


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

    import re as _re
    _ep = _re.escape(p)
    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{_ep}ترجمه(\s|$)"))
    async def translate(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        try:
            from bot.database import get_feature_flags
            flags = await get_feature_flags(uid) if uid else {}
            if not flags.get("trans_on", True):
                await event.edit("🔴 قابلیت ترجمه خاموش است. از پنل روشنش کن.")
                return
        except Exception:
            pass

        raw = event.raw_text or ""
        body = raw[len(p) + len("ترجمه"):].strip()
        if not body and event.is_reply:
            try:
                replied = await event.get_reply_message()
                body = (replied.raw_text or "").strip() if replied else ""
            except Exception:
                body = ""
        if not body:
            await event.edit(f"❌ متنی برای ترجمه پیدا نشد.\n\nمثال: <code>{p}ترجمه Hello world</code>", parse_mode="html")
            return

        to_persian = not bool(_PERSIAN.search(body)) or not body.strip()
        # If text has Persian chars → translate to English, else → Persian
        target = "fa" if not _PERSIAN.search(body) else "en"

        from selfbot.plugins.jesus_ai import get_ai_response
        if target == "fa":
            prompt = "متن زیر را به فارسی روان و طبیعی ترجمه کن. فقط ترجمه را بنویس، بدون توضیح.\n\n" + body
        else:
            prompt = "Translate the following Persian text into natural English. Only output the translation, no explanation.\n\n" + body
        try:
            result = (await get_ai_response(prompt) or "").strip() or "❌ ترجمه ناموفق بود."
        except Exception as e:
            result = f"❌ خطا: {e}"

        if len(result) > 3800:
            result = result[:3800] + "..."
        label = "انگلیسی → فارسی" if target == "fa" else "فارسی → انگلیسی"
        try:
            await event.edit(f"🌐 <b>ترجمه ({label}):</b>\n\n{result}", parse_mode="html")
        except Exception:
            try:
                await event.reply(f"🌐 **ترجمه ({label}):**\n\n{result}")
            except Exception:
                pass
