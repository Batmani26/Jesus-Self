"""Translator:
- `.ترجمه فارسی <text>` → translate English/text to Persian
- `.ترجمه انگلیسی <text>` → translate Persian/text to English
- If no target language given and command is just `.ترجمه`, auto-detect.
Edits the user's own message with the translation (no extra message).
"""
import re
from telethon import events

from selfbot.config import config

_LATIN = re.compile(r"[A-Za-z]")
_CYRILLIC = re.compile(r"[\u0400-\u04FF]")
_PERSIAN = re.compile(r"[\u0600-\u06FF]")


def _has_fa(text: str) -> bool:
    return bool(_PERSIAN.search(text))


def _has_en(text: str) -> bool:
    return bool(_LATIN.search(text))


async def _translate(text: str, target: str) -> str:
    """target: 'fa' or 'en'."""
    from selfbot.plugins.jesus_ai import get_ai_response
    if target == "fa":
        prompt = (
            "متن زیر را به فارسی روان و طبیعی ترجمه کن. "
            "فقط ترجمه را بنویس، بدون توضیح یا مقدمه.\n\n" + text
        )
    else:
        prompt = (
            "Translate the following text into natural English. "
            "Only output the translation, no explanation.\n\n" + text
        )
    res = await get_ai_response(prompt)
    return (res or "").strip()


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

    async def _get_text_and_target(event):
        raw = event.raw_text or ""
        body = raw[len(p) + len("ترجمه"):].strip()
        target = None
        if body.startswith("فارسی"):
            target = "fa"
            body = body[len("فارسی"):].strip()
        elif body.startswith("انگلیسی"):
            target = "en"
            body = body[len("انگلیسی"):].strip()

        # If no inline body, use replied message
        if not body and event.is_reply:
            try:
                replied = await event.get_reply_message()
                body = (replied.raw_text or "").strip() if replied else ""
            except Exception:
                body = ""

        if not target and body:
            target = "fa" if not _has_fa(body) else "en"
        return body, target

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{re.escape(p)}ترجمه(\s|$)"))
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

        text, target = await _get_text_and_target(event)
        if not text:
            await event.edit(
                f"❌ متن برای ترجمه پیدا نشد.\n\n"
                f"<code>{p}ترجمه فارسی Hello world</code>\n"
                f"<code>{p}ترجمه انگلیسی سلام دنیا</code>",
                parse_mode="html",
            )
            return
        if target not in ("fa", "en"):
            await event.edit("❌ زبان مقصد نامشخص است. از `فارسی` یا `انگلیسی` استفاده کن.")
            return

        try:
            result = await _translate(text, target)
            if not result:
                result = "❌ ترجمه ناموفق بود."
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
