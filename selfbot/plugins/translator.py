"""Translator: independent of AI providers (uses free Google Translate endpoint).

- `.ترجمه` (reply or inline text) → auto-detect:
    Latin/English text → Persian
    Persian text → English
Edits the user's own message in-place.
"""
import re
import json
import asyncio
import urllib.parse
import aiohttp
from telethon import events

from selfbot.config import config

_PERSIAN = re.compile(r"[\u0600-\u06FF]")


async def _gtranslate(text: str, target_lang: str) -> str:
    """Free Google Translate web endpoint — no API key required. Tries 3 hosts with retry."""
    q = urllib.parse.quote(text)
    timeout = aiohttp.ClientTimeout(total=15)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    hosts = [
        "translate.googleapis.com",
        "translate.google.com",
        "clients5.google.com",
    ]
    for host in hosts:
        url = (
            f"https://{host}/translate_a/single"
            f"?client=gtx&sl=auto&tl={target_lang}&dt=t&q={q}"
        )
        for attempt in range(2):
            try:
                async with aiohttp.ClientSession(timeout=timeout, headers=headers) as s:
                    async with s.get(url) as r:
                        if r.status != 200:
                            continue
                        data = await r.json(content_type=None)
                        out = []
                        for chunk in data[0] or []:
                            if chunk and chunk[0]:
                                out.append(chunk[0])
                        res = "".join(out).strip()
                        if res:
                            return res
            except Exception:
                pass
    return ""


async def _mymemory(text: str, target_lang: str) -> str:
    """Fallback: MyMemory free API."""
    try:
        q = urllib.parse.quote(text)
        pair = "fa|en" if target_lang == "en" else "en|fa"
        url = f"https://api.mymemory.translated.net/get?q={q}&langpair={pair}"
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return ""
                data = await r.json(content_type=None)
                return (data.get("responseData", {}).get("translatedText") or "").strip()
    except Exception:
        return ""


def _urllib_gtranslate_sync(text: str, target_lang: str) -> str:
    """Synchronous fallback via urllib (no aiohttp dependency)."""
    try:
        import urllib.request
        q = urllib.parse.quote(text)
        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=auto&tl={target_lang}&dt=t&q={q}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            raw = r.read().decode("utf-8", errors="ignore")
        import json as _j
        data = _j.loads(raw)
        out = []
        for chunk in data[0] or []:
            if chunk and chunk[0]:
                out.append(chunk[0])
        return "".join(out).strip()
    except Exception:
        return ""


async def _libretranslate(text: str, target_lang: str) -> str:
    """Fallback: LibreTranslate free instance."""
    try:
        url = "https://libretranslate.com/translate"
        payload = {"q": text, "source": "auto", "target": target_lang, "format": "text"}
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.post(url, json=payload) as r:
                if r.status != 200:
                    return ""
                data = await r.json(content_type=None)
                return (data.get("translatedText") or "").strip()
    except Exception:
        return ""


async def _translate(text: str, target_lang: str) -> str:
    # Race both endpoints in parallel, first non-empty wins (fast)
    tasks = [
        asyncio.create_task(_gtranslate(text, target_lang)),
        asyncio.create_task(_mymemory(text, target_lang)),
    ]
    for coro in asyncio.as_completed(tasks):
        try:
            r = await coro
        except Exception:
            r = ""
        if r:
            for t in tasks:
                if not t.done():
                    t.cancel()
            return r
    # Final fallback: synchronous urllib via thread (bypasses any aiohttp issues)
    try:
        r = await asyncio.to_thread(_urllib_gtranslate_sync, text, target_lang)
        if r:
            return r
    except Exception:
        pass
    r = await _libretranslate(text, target_lang)
    return r


def register(client) -> None:
    import re as _re
    _ep = _re.escape(config.PREFIX)
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{_ep}ترجمه(\s|$)"))
    async def translate(event: events.NewMessage.Event) -> None:
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

        target = "fa" if not _PERSIAN.search(body) else "en"
        label = "انگلیسی → فارسی" if target == "fa" else "فارسی → انگلیسی"

        result = await _translate(body, target)
        if not result:
            result = "❌ سرویس ترجمه در دسترس نیست. کمی بعد دوباره تلاش کن."
        if len(result) > 3800:
            result = result[:3800] + "..."
        try:
            await event.edit(f"🌐 <b>ترجمه ({label}):</b>\n\n{result}", parse_mode="html")
        except Exception:
            try:
                await event.reply(f"🌐 **ترجمه ({label}):**\n\n{result}")
            except Exception:
                pass
