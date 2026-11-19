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
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    data = {"contents": contents}
    if system:
        data["systemInstruction"] = {"parts": [{"text": system}]}
    # Try models in order — Google deprecates old ones for new keys
    for model in ("gemini-flash-lite-latest", "gemini-3.1-flash-lite", "gemini-3.1-flash-lite-preview", "gemini-flash-latest"):
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={GEMINI_API_KEY}"
        )
        res = await _post_json(url, {}, data)
        if res:
            try:
                txt = res["candidates"][0]["content"]["parts"][0]["text"]
                if txt:
                    return txt
            except (KeyError, IndexError):
                continue
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
    """Free fallback (no API key needed). Try better models first."""
    s = await _get_session()
    full = f"{system}\n\nUser: {prompt}" if system else prompt
    # Keep prompt compact for GET-based endpoint (avoid overly long URLs)
    if len(full) > 2500:
        full = full[:2500]
    from urllib.parse import quote as _q
    proxy = getattr(s, "_magnum_proxy", None)
    for model in ("openai", ""):
        try:
            url = "https://text.pollinations.ai/" + _q(full, safe="")
            if model:
                url += f"?model={model}"
            async with s.get(
                url,
                timeout=aiohttp.ClientTimeout(total=25),
                proxy=proxy,
            ) as resp:
                if resp.status == 200:
                    txt = await resp.text()
                    if txt and len(txt.strip()) > 5:
                        return txt
        except Exception as e:
            print(f"[AI] pollinations {model} error: {type(e).__name__}")
            continue
    return None


SYSTEM_PROMPT = (
    "You are 'جیزس' (Jesus), a precise, reliable Persian AI assistant in a Telegram bot. "
    "Your NUMBER ONE priority is ACCURACY and CLARITY — never produce random, incoherent, or nonsensical text. "
    "Always answer in fluent, natural, grammatically correct Persian (فارسی). "
    "Think step by step internally, then give a clear, well-structured, complete answer. "
    "For jokes/stories: they must be genuinely funny, logically coherent, with a clear setup and punchline — "
    "NEVER output gibberish, random words, or mixed nonsense sentences. If unsure, give a short honest answer instead. "
    "Do NOT mention any brand, bot name, or promotional line. Do not use filler. "
    "When web results are provided, treat them as ground truth and extract the exact numbers/facts. "
    "Answer the user's question directly FIRST, then add detail. "
    "Only add a source line at the very end if a real URL literally appears in the provided web results, formatted as: '🔗 منبع: <url>'. "
    "CRITICAL: NEVER invent or guess a URL. If no real URL is present, do NOT add any source line. "
    "If you don't know something and no web data is given, say so honestly in Persian."
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

# Verbs/cues that indicate the user actually WANTS an image (not code/scripts about images)
_IMG_REQUEST_CUES = (
    "بفرست", "بده", "نشان", "نشون", "پیدا", "جستجو", "سرچ", "بگرد",
    "send", "show", "find", "search", "give", "get",
)
# If the prompt asks for CODE/SCRIPT, never treat it as an image request
_CODE_CUES = ("اسکریپت", "کد", "برنامه", "script", "code", "function", "تابع", "python", "پایتون", "بنویس", "write")

def _needs_image(text: str) -> bool:
    low = text.lower()
    if not any(k in low for k in _IMG_KEYWORDS):
        return False
    # Reject if it's a coding request
    if any(k in low for k in _CODE_CUES):
        return False
    # Require an actual request cue (otherwise just mentioning 'عکس' is not an image request)
    return any(k in low for k in _IMG_REQUEST_CUES)


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
    # Strip Persian/English filler to get a cleaner title
    clean = query
    for w in ("عکس‌های", "عکسهای", "عکس", "تصاویر", "تصویر", "پیکچر", "رو بده", "بده", "نشان بده",
              "از", "رو", "please", "photo", "image", "picture", "pic", "show", "me"):
        clean = clean.replace(w, " ")
    clean = " ".join(clean.split()).strip() or query
    # Fix trailing conjunction like 'میلادو' -> 'میلاد'
    if clean.endswith("و") and len(clean) > 2:
        clean = clean[:-1].strip()

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


async def _fetch(url: str, proxy, retries: int = 1, timeout: float = 6.0) -> str | None:
    """Fast single-attempt fetch (proxy then direct). Keep timeouts short for speed."""
    s = await _get_session()
    for p in ([proxy, None] if proxy else [None]):
        try:
            async with s.get(url, proxy=p, timeout=aiohttp.ClientTimeout(total=timeout),
                             headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                                      "Cache-Control": "no-cache, no-store, must-revalidate",
                                      "Pragma": "no-cache"}) as r:
                if r.status == 200:
                    return await r.text(errors="ignore")
        except Exception:
            continue
    return None


async def _ddg_snippets(query: str, proxy) -> str | None:
    from urllib.parse import quote as _q
    import re as _re
    html = await _fetch("https://html.duckduckgo.com/html/?q=" + _q(query), proxy)
    if not html:
        return None
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
    lines, srcs = [], []
    for i in range(min(5, len(snippets))):
        t = _clean(titles[i]) if i < len(titles) else ""
        sn = _clean(snippets[i])
        if sn:
            lines.append(f"- {t}: {sn}" if t else f"- {sn}")
        if i < len(hrefs):
            u = _real_url(hrefs[i])
            if u and u not in srcs:
                srcs.append(u)
    out = ""
    if lines:
        out += "نتایج جستجوی وب:\n" + "\n".join(lines)
    if srcs:
        out += "\nلینک منابع:\n" + "\n".join(srcs[:3])
    return out or None


async def _fx_usd_irr(proxy) -> str | None:
    # Fast free FX sources; try in parallel, first that yields wins
    async def _erapi():
        raw = await _fetch("https://open.er-api.com/v6/latest/USD", proxy)
        if not raw:
            return None
        try:
            import json as _json
            d = _json.loads(raw)
            irr = d.get("rates", {}).get("IRR")
            if irr:
                toman = round(irr / 10)
                return f"نرخ دلار: {irr:,.0f} ریال ({toman:,.0f} تومان) — منبع: https://open.er-api.com/v6/latest/USD"
        except Exception:
            return None
        return None

    async def _tgju():
        raw = None
        for host in ("call1.tgju.org", "call2.tgju.org", "call3.tgju.org", "call.tgju.org"):
            raw = await _fetch(f"https://{host}/ajax.json", proxy, timeout=10)
            if raw:
                break
        if not raw:
            return None
        try:
            import json as _json
            d = _json.loads(raw)
            cur = d.get("current", {})
            def _num(k):
                node = cur.get(k)
                if isinstance(node, dict):
                    return node.get("p")
                return None
            p = _num("price_dollar_rl")
            if p:
                # p is in Rial, e.g. '2,679,000' -> toman = /10
                try:
                    rial = float(str(p).replace(",", ""))
                    toman = rial / 10
                    line = (
                        f"نرخ دلار بازار آزاد (TGJU): {int(rial):,} ریال "
                        f"= {int(toman):,} تومان"
                    )
                except Exception:
                    line = f"نرخ دلار بازار آزاد (TGJU): {p} ریال"
                extras = []
                for k, label, div in (("price_eur", "یورو", 10), ("price_gbp", "پوند", 10),
                                       ("price_aed", "درهم", 10), ("price_try", "لیر", 10)):
                    v = _num(k)
                    if v:
                        try:
                            extras.append(f"{label}: {int(float(str(v).replace(',',''))/div):,} تومان")
                        except Exception:
                            pass
                if extras:
                    line += " | " + "، ".join(extras)
                line += " — منبع: https://www.tgju.org/profile/price_dollar_rl"
                return line
        except Exception:
            return None
        return None

    # Prefer TGJU (Iranian free-market rate) — it is the accurate source for Iran.
    # Fall back to open.er-api (global official rate) only if TGJU fails.
    tgju_task = asyncio.create_task(_tgju())
    erapi_task = asyncio.create_task(_erapi())
    try:
        r = await asyncio.wait_for(tgju_task, timeout=12.0)
    except Exception:
        r = None
    if r:
        if not erapi_task.done():
            erapi_task.cancel()
        return r
    # TGJU failed → use er-api (mark it as global/official, not free-market)
    try:
        r2 = await asyncio.wait_for(erapi_task, timeout=5.0)
    except Exception:
        r2 = None
    if r2:
        return r2 + " (نرخ جهانی/رسمی — بازار آزاد ایران معمولاً بالاتر است)"
    return None


async def _weather(query: str, proxy) -> str | None:
    """Free weather via wttr.in (no key)."""
    import re as _re
    q = query
    for w in ("هوا", "آب و هوا", "امروز", "فردا", "چطوره", "چطور است", "خوبه یا بده", "weather", "today", "how is"):
        q = q.replace(w, " ")
    q = " ".join(q.split()).strip() or "Tehran"
    try:
        from urllib.parse import quote as _q
        raw = await _fetch(f"https://wttr.in/{_q(q)}?format=j1", proxy, timeout=8)
        if raw:
            import json as _json
            d = _json.loads(raw)
            cur = d.get("current_condition", [{}])[0]
            desc = cur.get("weatherDesc", [{}])[0].get("value", "")
            temp = cur.get("temp_C", "?")
            feels = cur.get("FeelsLikeC", "?")
            hum = cur.get("humidity", "?")
            return f"آب‌وهوای {q}: {desc}، دما {temp}°C (احساس {feels}°C)، رطوبت {hum}% — منبع: wttr.in"
    except Exception as e:
        print(f"[AI-web] weather error: {e}")
    return None


async def _web_search(query: str) -> str:
    """Fast parallel web digest: FX + weather + DDG snippets, hard-capped to ~8s."""
    s = await _get_session()
    proxy = getattr(s, "_magnum_proxy", None)
    ql = query.lower()
    jobs = []
    if any(w in ql for w in ("دلار", "ریال", "تومان", "usd", "irr", "price", "نرخ", "یورو", "eur")):
        jobs.append(asyncio.create_task(_fx_usd_irr(proxy)))
    if any(w in ql for w in ("هوا", "آب و هوا", "weather", "دما", "باران", "برف")):
        jobs.append(asyncio.create_task(_weather(query, proxy)))
    jobs.append(asyncio.create_task(_ddg_snippets(query, proxy)))

    parts = []
    try:
        done, pending = await asyncio.wait(jobs, timeout=6.0)
        for t in pending:
            t.cancel()
        for t in jobs:
            if t.done() and not t.cancelled():
                try:
                    r = t.result()
                except Exception:
                    r = None
                if r:
                    parts.append(r)
    except Exception as e:
        print(f"[AI-web] search error: {e}")
    return "\n\n".join(parts)[:2600]


async def get_ai_response(prompt: str) -> str:
    """Race all configured providers; first non-empty answer wins."""
    # Only include providers that actually have a key configured
    providers = []
    if GEMINI_API_KEY:
        providers.append(("gemini", get_gemini_response))
    if XAI_API_KEY:
        providers.append(("grok", get_grok_response))
    if GROQ_API_KEY:
        providers.append(("groq", get_groq_response))
    if OPENAI_API_KEY:
        providers.append(("openai", get_openai_response))
    print(f"[AI] providers with keys: {[n for n,_ in providers]}")
    if not providers:
        # No keys at all -> go straight to free fallback
        res = await get_pollinations_response(prompt, SYSTEM_PROMPT)
        return res or "❌ هیچ کلید AI تنظیم نشده. از پنل یا .env کلید اضافه کن."

    async def try_one(name, fn):
        try:
            r = await asyncio.wait_for(fn(prompt, SYSTEM_PROMPT), timeout=15)
            if not r:
                print(f"[AI] {name} returned empty")
            return r
        except Exception as e:
            print(f"[AI] {name} error: {type(e).__name__}: {e}")
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
    import re as _re
    p = config.PREFIX
    _ep = _re.escape(p)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{_ep}جیزس (.+)$"))
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

        # Fast local date answer (no AI needed)
        _date_kw = ("امروز چندمه", "تاریخ امروز", "چندم ماهه", "today's date", "امروز چه تاریخیه")
        if any(k in prompt for k in _date_kw) and "هوا" not in prompt:
            import datetime, pytz
            try:
                from persiantools.jdatetime import JalaliDate
                now = datetime.datetime.now(pytz.timezone("Asia/Tehran"))
                jdate = JalaliDate(now).strftime("%Y/%m/%d")
                await event.reply(f"📅 **امروز:**\nشمسی: `{jdate}`\nمیلادی: `{now.strftime('%Y/%m/%d')}`\n⏰ ساعت: `{now.strftime('%H:%M')}`")
            except Exception:
                now = datetime.datetime.now()
                await event.reply(f"📅 امروز: `{now.strftime('%Y/%m/%d')}`")
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
