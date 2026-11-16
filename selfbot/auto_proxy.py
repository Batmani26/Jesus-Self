"""Auto-proxy: keep a working proxy for Telegram even behind filtering.

On Render/foreign servers api.telegram.org is reachable directly -> no proxy needed.
On filtered networks this fetches/tests local proxies and selects a working one.
"""
import asyncio
import logging
import os
import socket

import aiohttp

log = logging.getLogger("selfbot.auto_proxy")

TG_HOST = "api.telegram.org"
TG_PORT = 443

CANDIDATE_PROXIES = [
    os.getenv("TG_PROXY", "").strip(),
    "http://127.0.0.1:10809",
    "http://127.0.0.1:12334",
    "http://127.0.0.1:2334",
    "http://127.0.0.1:7890",
    "http://127.0.0.1:2080",
    "socks5://127.0.0.1:10808",
    "socks5://127.0.0.1:12335",
]
CANDIDATE_PROXIES = [p for p in CANDIDATE_PROXIES if p]


def _tcp_reachable(host: str, port: int, timeout: float = 6.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


async def _http_proxy_works(proxy_url: str, timeout: float = 8.0) -> bool:
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as s:
            async with s.get(f"https://{TG_HOST}/", proxy=proxy_url, ssl=False) as resp:
                return resp.status < 600
    except Exception:
        return False


async def detect_best_proxy() -> str | None:
    if _tcp_reachable(TG_HOST, TG_PORT):
        log.info("[auto_proxy] Direct Telegram reachable - no proxy needed.")
        return None
    log.warning("[auto_proxy] Direct Telegram blocked. Probing local proxies...")
    for proxy in CANDIDATE_PROXIES:
        try:
            ok = await _http_proxy_works(proxy)
        except Exception:
            ok = False
        if ok:
            log.info(f"[auto_proxy] Working proxy found: {proxy}")
            return proxy
    log.error(
        "[auto_proxy] No working proxy found and direct Telegram blocked. "
        "Start a local VPN/proxy or set TG_PROXY in env."
    )
    return None


async def ensure_proxy_env(force: bool = False) -> str | None:
    current = os.getenv("TG_PROXY", "").strip()
    if current and not force:
        return current or None
    best = await detect_best_proxy()
    if best:
        os.environ["TG_PROXY"] = best
    return best


async def proxy_refresh_loop(interval_seconds: int = 600):
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            if _tcp_reachable(TG_HOST, TG_PORT):
                continue
            log.warning("[auto_proxy] Telegram became unreachable - re-detecting proxy.")
            await detect_best_proxy()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.error(f"[auto_proxy] refresh error: {e}")
