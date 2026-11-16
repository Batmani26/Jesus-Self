"""Jesus AI plugin: `.جیزس <text>` — multi-provider AI with Grok, Gemini, Groq.

Optimizations:
- Shared aiohttp session (connection pooling) → much faster
- Parallel race: fastest provider wins
- Grok (xAI) support
- Robust error handling + retry
"""
import aiohttp
import asyncio
import os
from telethon import events
from selfbot.config import config

# API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
XAI_API_KEY = os.getenv("XAI_API_KEY", "")  # Grok
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Shared HTTP session (created lazily) — connection pooling for speed
_session: aiohttp.ClientSession | None = None


async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        # Optional outbound proxy for filtered regions (e.g. Iran).
        # Set AI_PROXY=socks5://127.0.0.1:10808 (v2rayN local SOCKS) or
        # AI_PROXY=http://127.0.0.1:10809 in .env to route AI requests via your VPN.
        proxy = os.getenv("AI_PROXY", "").strip() or None
        _session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=25),
            connector=aiohttp.TCPConnector(limit=50, ttl_dns_cache=300),
        )
        _session._magnum_proxy = proxy
    return _session


async def _post_json(url: str, headers: dict, data: dict) -> dict | None:
    s = await _get_session()
    proxy = getattr(s, "_magnum_proxy", None)
    # Try proxy first, then fall back to direct if proxy is dead
    for p in ([proxy, None] if proxy else [None]):
        try:
            async with s.post(url, headers=headers, json=data, proxy=p) as resp:
                if resp.status == 200:
                    return await resp.json()
                if resp.status >= 400:
                    body = await resp.text()
                    print(f"[AI] {url.split('/')[2]} HTTP {resp.status}: {body[:150]}")
                    return None
        except Exception as e:
            print(f"[AI] post {'proxy' if p else 'direct'} fail {url.split('/')[2]}: {type(e).__name__}")
            continue
    return None


async def get_grok_response(prompt: str, system: str = "") -> str | None:
    """xAI Grok via OpenAI-compatible endpoint."""
    if not XAI_API_KEY:
        return None
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    data = {"model": "grok-2-latest", "messages": messages, "temperature": 0.7, "max_tokens": 1024}
    res = await _post_json(url, headers, data)
    if res:
        try:
            return res["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            pass
    return None


async def get_groq_response(prompt: str, system: str = "") -> str | None:
    if not GROQ_API_KEY:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    data = {"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 1024}
    res = await _post_json(url, headers, data)
    if res:
        try:
            return res["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            pass
    return None


async def get_gemini_response(prompt: str, system: str = "") -> str | None:
    if not GEMINI_API_KEY:
        return None
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    )
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    data = {"contents": contents}
    if system:
        data["systemInstruction"] = {"parts": [{"text": system}]}
    res = await _post_json(url, {}, data)
    if res:
        try:
            return res["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            pass
    return None


async def get_openai_response(prompt: str, system: str = "") -> str | None:
    if not OPENAI_API_KEY:
        return None
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    data = {"model": "gpt-4o-mini", "messages": messages, "max_tokens": 1024}
    res = await _post_json(url, headers, data)
    if res:
        try:
            return res["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            pass
    return None


async def get_pollinations_response(prompt: str, system: str = "") -> str | None:
    """Free fallback (no API key needed)."""
    try:
        s = await _get_session()
        full = f"{system}\n\nUser: {prompt}" if system else prompt
        from urllib.parse import quote as _q
        proxy = getattr(s, "_magnum_proxy", None)
        async with s.get(
            "https://text.pollinations.ai/" + _q(full, safe="") + "?model=openai",
            timeout=aiohttp.ClientTimeout(total=30),
            proxy=proxy,
        ) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception as e:
        print(f"[AI] pollinations error: {e}")
    return None


SYSTEM_PROMPT = (
    "You are 'جیزس' (Jesus), the AI assistant of the 'Jesus Self' Telegram bot. "
    "You are proud to be part of Jesus Self. If asked, praise Jesus Self for its speed, security, and features. "
    "Answer concisely in Persian (فارسی). Be helpful, accurate and friendly. "
    "If unsure, say so honestly. "
    "When web search results are provided, use them as the source of truth and cite them briefly."
)


# ---------- Web search / live info ----------
_WEB_KEYWORDS = (
    "قیمت", "چنده", "چند است", "نرخ", "دلار", "یورو", "طلا", "سکه", "بیتکوین", "بیت کوین",
    "اخبار", "خبر", "امروز", "آخرین", "جدیدترین", "آب و هوا", "هوا", "نتیجه", "بازی",
    "price", "rate", "news", "weather", "today", "latest", "score", "usd", "eur",
)


def _needs_web(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in _WEB_KEYWORDS)


async def _fetch(url: str, proxy) -> str | None:
    s = await _get_session()
    for p in ([proxy, None] if proxy else [None]):
        try:
            async with s.get(url, proxy=p, timeout=aiohttp.ClientTimeout(total=12),
                             headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as r:
                if r.status == 200:
                    return await r.text(errors="ignore")
        except Exception as e:
            print(f"[AI-web] fetch {'proxy' if p else 'direct'} fail {url[:40]}: {type(e).__name__}")
            continue
    return None


async def _web_search(query: str) -> str:
    """Return a compact text digest of web results (DDG HTML + currency API)."""
    s = await _get_session()
    proxy = getattr(s, "_magnum_proxy", None)
    parts = []

    # 1) Live currency (free, no key) for price queries
    ql = query.lower()
    if any(w in ql for w in ("دلار", "یورو", "usd", "eur", "درهم", "لیر", "price", "نرخ")):
        try:
            from urllib.parse import quote as _q
            fr = await _fetch("https://api.frankfurter.app/latest?from=USD&to=EUR,GBP,TRY,AED", proxy)
            if fr:
                import json as _json
                d = _json.loads(fr).get("rates", {})
                if d:
                    parts.append("نرخ ارز (Frankfurter, base USD): " + ", ".join(f"{k}={v}" for k, v in d.items()))
        except Exception:
            pass

    # 2) DuckDuckGo HTML results
    try:
        from urllib.parse import quote as _q
        import re as _re
        html = await _fetch("https://html.duckduckgo.com/html/?q=" + _q(query), proxy)
        if html:
            # extract result titles + snippets
            snippets = _re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, _re.S)
            titles = _re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, _re.S)
            def _clean(x):
                x = _re.sub(r'<[^>]+>', '', x)
                return _re.sub(r'\s+', ' ', x).strip()
            lines = []
            for i in range(min(5, len(snippets))):
                t = _clean(titles[i]) if i < len(titles) else ""
                sn = _clean(snippets[i])
                if sn:
                    lines.append(f"- {t}: {sn}" if t else f"- {sn}")
            if lines:
                parts.append("نتایج جستجوی وب:\n" + "\n".join(lines))
    except Exception as e:
        print(f"[AI-web] ddg error: {e}")

    return "\n\n".join(parts)[:2500]


async def get_ai_response(prompt: str) -> str:
    """Race all configured providers; first non-empty answer wins."""
    providers = [
        ("grok", get_grok_response),
        ("gemini", get_gemini_response),
        ("groq", get_groq_response),
        ("openai", get_openai_response),
    ]

    async def try_one(name, fn):
        try:
            return await asyncio.wait_for(fn(prompt, SYSTEM_PROMPT), timeout=20)
        except Exception:
            return None

    tasks = [asyncio.create_task(try_one(n, f)) for n, f in providers]
    for coro in asyncio.as_completed(tasks):
        result = await coro
        if result:
            for t in tasks:
                if not t.done():
                    t.cancel()
            return result

    # Slow fallback
    res = await get_pollinations_response(prompt, SYSTEM_PROMPT)
    if res:
        return res
    return "❌ متاسفانه در حال حاضر سرویس‌های هوش مصنوعی پاسخ ندادن. (ممکنه محدودیت درخواست باشه، چند دقیقه دیگه امتحان کن)"


def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}جیزس (.+)$"))
    async def jesus_ai(event: events.NewMessage.Event) -> None:
        prompt = event.pattern_match.group(1).strip()

        context_keywords = ["گپ", "چت", "اینجا", "این گروه", "این چت"]
        is_chat_question = any(k in prompt for k in context_keywords)

        context_text = ""
        if is_chat_question:
            try:
                messages = await client.get_messages(event.chat_id, limit=10)
                context_lines = []
                for m in reversed(messages):
                    if m.text:
                        sender = await m.get_sender()
                        name = getattr(sender, "first_name", "Unknown")
                        context_lines.append(f"{name}: {m.text}")
                context_text = "\n\nContext of recent messages in this chat:\n" + "\n".join(context_lines)
            except Exception:
                pass

        web_text = ""
        if _needs_web(prompt):
            web_text = await _web_search(prompt)

        full_prompt = f"User Question: {prompt}{context_text}"
        if web_text:
            full_prompt += f"\n\n[نتایج زنده از وب — از این‌ها به‌عنوان منبع استفاده کن]:\n{web_text}"

        status_msg = await event.reply("⏳ در حال فکر کردن..." if not web_text else "🌐 در حال جستجو در وب...")
        response = await get_ai_response(full_prompt)
        if len(response) > 4000:
            response = response[:4000] + "..."
        try:
            await status_msg.edit(f"🤖 **جیزس:**\n\n{response}")
        except Exception:
            await event.reply(f"🤖 **جیزس:**\n\n{response}")
