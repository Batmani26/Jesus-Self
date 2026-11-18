"""Translator: `.ترجمه <text>` detects EN/RU and translates to Persian."""
import re
from telethon import events

from selfbot.config import config

_LATIN = re.compile(r"[A-Za-z]")
_CYRILLIC = re.compile(r"[\u0400-\u04FF]")
_PERSIAN = re.compile(r"[\u0600-\u06FF]")


def detect_lang(text: str) -> str:
    if _CYRILLIC.search(text):
        return "روسی"
    if _LATIN.search(text):
        return "انگلیسی"
    return "نامشخص"


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

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}ترجمه (.+)$"))
    async def translate(event: events.NewMessage.Event) -> None:
        uid = await _own_id()
        try:
            from bot.database import get_feature_flags
            flags = await get_feature_flags(uid) if uid else {}
            if not flags.get("trans_on", True):
                await event.reply("🔴 قابلیت ترجمه خاموش است. از پنل روشنش کن.")
                return
        except Exception:
            pass

        text = event.pattern_match.group(1).strip()
        lang = detect_lang(text)
        status = await event.reply("🌐 در حال ترجمه...")

        # Use the AI plugin's providers
        try:
            from selfbot.plugins.jesus_ai import get_ai_response
            prompt = (
                f"متن زیر به زبان {lang} است. آن را به فارسی روان و طبیعی ترجمه کن. "
                f"فقط ترجمه را بنویس، بدون توضیح اضافه.\n\n{text}"
            )
            result = await get_ai_response(prompt)
            if not result:
                result = "❌ ترجمه ناموفق بود. دوباره تلاش کن."
        except Exception as e:
            result = f"❌ خطا: {e}"

        if len(result) > 4000:
            result = result[:4000] + "..."
        try:
            await status.edit(
                f"🌐 **ترجمه ({lang} → فارسی):**\n\n{result}"
            )
        except Exception:
            await event.reply(f"🌐 **ترجمه ({lang} → فارسی):**\n\n{result}")
