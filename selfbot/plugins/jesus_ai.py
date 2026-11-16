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
    "You are 'جیزس' (Jesus), a warm, friendly and knowledgeable AI assistant in a Telegram bot. "
    "Always answer in fluent Persian (فارسی). Be conversational, warm and helpful — like a smart friend. "
    "Give a clear, complete answer (not too short). "
    "Do NOT mention or advertise any brand/bot name; never write promotional lines. "
    "When web search results are provided, rely on them as the source of truth, extract the exact numbers/answers, "
    "answer the user's question directly FIRST, and then at the very end list the source link(s) on a new line as: "
    "'🔗 منبع: <url>'. "
    "If the data isn't in the results, say so honestly and suggest the best source."
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


_IMG_KEYWORDS = ("عکس", "تصویر", "پیکچر", "photo", "image", "picture", "pic")

def _needs_image(text: str) -> bool:
    low = text.lower()
    return any(k in low for k in _IMG_KEYWORDS)


def _img_ok(u: str) -> bool:
    ul = u.lower().split("?", 1)[0].split("#", 1)[0]  # strip query/fragment
    bad = ("logo", "icon", "outline", "flag", ".svg", "placeholder", "question")
    if any(b in ul for b in bad):
        return False
    return ul.endswith((".jpg", ".jpeg", ".png", ".webp"))


async def _wiki_media(title: str, limit: int, lang: str = "en") -> list[dict]:
    """Best real photos via Wikipedia media-list API (open license, no key)."""
    from urllib.parse import quote as _q
    results = []
    url = (f"https://{lang}.wikipedia.org/api/rest_v1/page/media-list/" + _q(title.replace(" ", "_")))
    raw = await _fetch(url, None)
    if not raw:
        return results
    try:
        import json as _json
        d = _json.loads(raw)
        for it in d.get("items", []):
            if it.get("type") != "image":
                continue
            srcset = it.get("srcset") or []
            if not srcset:
                continue
            src = srcset[-1].get("src") or srcset[0].get("src") or ""
            if src.startswith("//"):
                src = "https:" + src
            if _img_ok(src):
                results.append({"url": src, "title": it.get("title", title) or title})
            if len(results) >= limit:
                break
    except Exception as e:
        print(f"[AI-img] wiki media error: {e}")
    return results


async def _image_search(query: str, limit: int = 6) -> list[dict]:
    """Fetch real open-source photos: Wikipedia media-list + Commons, with retries."""
    # Strip Persian filler to get a cleaner title
    clean = query
    for w in ("عکس", "تصویر", "پیکچر", "رو بده", "بده", "از", "رو", "please", "photo", "image"):
        clean = clean.replace(w, " ")
    clean = " ".join(clean.split()).strip() or query

    # Detect Persian to pick the right Wikipedia
    is_fa = any("\u0600" <= ch <= "\u06FF" for ch in clean)
    langs = ["fa", "en"] if is_fa else ["en", "fa"]

    results = []
    # 1) Wikipedia page media (best quality/relevance)
    for lang in langs:
        for title in (clean, query):
            try:
                got = await _wiki_media(title, limit, lang)
            except Exception:
                got = []
            if got:
                results.extend(got)
                break
            await asyncio.sleep(0.8)  # avoid 429
        if results:
            break

    # 2) Wikipedia search -> first hit page media
    if not results:
        try:
            from urllib.parse import quote as _q
            import json as _json
            for lang in langs:
                sapi = (f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch="
                        + _q(clean) + "&format=json&srlimit=1")
                raw = await _fetch(sapi, None)
                if raw:
                    hits = _json.loads(raw).get("query", {}).get("search", [])
                    if hits:
                        results = await _wiki_media(hits[0]["title"], limit, lang)
                        if results:
                            break
                await asyncio.sleep(0.8)
        except Exception as e:
            print(f"[AI-img] wiki search error: {e}")

    # Dedupe
    seen = set()
    out = []
    for r in results:
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        out.append(r)
    return out[:limit]


async def _download_bytes(url: str) -> bytes | None:
    s = await _get_session()
    proxy = getattr(s, "_magnum_proxy", None)
    for p in ([proxy, None] if proxy else [None]):
        try:
            async with s.get(url, proxy=p, timeout=aiohttp.ClientTimeout(total=20),
                             headers={"User-Agent": "Mozilla/5.0"}) as r:
                if r.status == 200:
                    data = await r.read()
                    if data and len(data) > 2048:
                        return data
        except Exception:
            continue
    return None


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

    # 2) Live Iran FX (USD->Toman/Rial) via public JSON APIs
    if any(w in ql for w in ("دلار", "ریال", "تومان", "usd", "irr")):
        for fxurl in (
            "https://api.tgju.org/v1/market/indicator/summary-table-data/price_dollar_rl",
            "https://call1.tgju.org/ajax.json",
        ):
            try:
                raw = await _fetch(fxurl, proxy)
                if raw and len(raw) < 20000:
                    import json as _json
                    d = _json.loads(raw)
                    # try common shapes
                    price = None
                    if isinstance(d, dict):
                        cur = d.get("current") or d.get("price") or {}
                        if isinstance(cur, dict):
                            price = cur.get("p") or cur.get("price")
                    if price:
                        parts.append(f"نرخ دلار (ریال، منبع TGJU): {price}")
                        break
            except Exception:
                continue

    # 3) DuckDuckGo HTML results (with source links)
    try:
        from urllib.parse import quote as _q
        import re as _re
        html = await _fetch("https://html.duckduckgo.com/html/?q=" + _q(query), proxy)
        if html:
            snippets = _re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, _re.S)
            titles = _re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, _re.S)
            hrefs = _re.findall(r'class="result__a"[^>]*href="(.*?)"', html, _re.S)
            def _clean(x):
                x = _re.sub(r'<[^>]+>', '', x)
                return _re.sub(r'\s+', ' ', x).strip()
            def _real_url(h):
                m2 = _re.search(r'uddg=([^&]+)', h)
                if m2:
                    from urllib.parse import unquote as _u
                    return _u(m2.group(1))
                return h if h.startswith("http") else ""
            lines = []
            srcs = []
            for i in range(min(5, len(snippets))):
                t = _clean(titles[i]) if i < len(titles) else ""
                sn = _clean(snippets[i])
                if sn:
                    lines.append(f"- {t}: {sn}" if t else f"- {sn}")
                if i < len(hrefs):
                    u = _real_url(hrefs[i])
                    if u and u not in srcs:
                        srcs.append(u)
            if lines:
                parts.append("نتایج جستجوی وب:\n" + "\n".join(lines))
            if srcs:
                parts.append("لینک منابع:\n" + "\n".join(srcs[:3]))
    except Exception as e:
        print(f"[AI-web] ddg error: {e}")

    return "\n\n".join(parts)[:2800]


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

        # Image request branch
        if _needs_image(prompt):
            status = await event.reply("🖼 در حال جستجوی تصاویر...")
            imgs = await _image_search(prompt, limit=6)
            sent = 0
            for it in imgs:
                data = await _download_bytes(it["url"])
                if not data:
                    continue
                try:
                    await client.send_file(event.chat_id, file=data, caption=(it.get("title") or "")[:200])
                    sent += 1
                except Exception as e:
                    print(f"[AI-img] send fail: {e}")
                if sent >= 3:
                    break
            try:
                if sent == 0:
                    await status.edit("❌ تصویری پیدا نشد. دوباره تلاش کن.")
                else:
                    await status.edit(f"✅ {sent} تصویر ارسال شد. 🤖 Jesus")
            except Exception:
                pass
            return

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
