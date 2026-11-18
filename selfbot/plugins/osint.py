"""OSINT plugin: Stalk & Security.
The query is executed via the ADMIN account (source of truth) and only the
result is delivered to the requesting user's Saved Messages.
"""
import asyncio
import re
import logging
from telethon import events

from selfbot.config import config

log = logging.getLogger("selfbot.osint")
TARGET_BOT = "@funstatloper_bot"
USER_STATES = {}


def _clean(txt: str) -> str:
    return re.sub(r"\s+", " ", txt or "").strip()


async def _run_osint(admin_client, target: str) -> str | None:
    """Ask the target bot via admin client; return cleaned answer or None."""
    for attempt in range(2):
        try:
            async with admin_client.conversation(TARGET_BOT, timeout=20) as conv:
                sent = await conv.send_message(target)
                try:
                    await sent.delete()
                except Exception:
                    pass
                deadline = asyncio.get_event_loop().time() + 18
                last = ""
                while asyncio.get_event_loop().time() < deadline:
                    try:
                        resp = await asyncio.wait_for(conv.get_response(), timeout=8)
                    except asyncio.TimeoutError:
                        break
                    txt = resp.text or ""
                    try:
                        await resp.delete()
                    except Exception:
                        pass
                    if not txt:
                        continue
                    clean = _clean(txt)
                    low = clean.lower()
                    if any(k in low for k in ("searching", "looking", "loading", "wait", "⏳")) or len(clean) < 30:
                        last = clean
                        continue
                    return clean
                if last and len(last) >= 10:
                    return last
        except Exception as e:
            log.warning(f"OSINT attempt {attempt+1} failed: {type(e).__name__} - {e}")
            await asyncio.sleep(1.5)
    return None


def register(client) -> None:
    import re as _re
    _ep = _re.escape(config.PREFIX)
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{_ep}استاک$"))
    async def osint_cmd(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        USER_STATES[me.id] = "WAITING_TARGET"
        try:
            await event.delete()
        except Exception:
            pass
        await client.send_message(
            "me",
            "🛡 **بخش استاک و امنیت**\n\n"
            "لطفاً **آیدی عددی** یا **یوزرنیم** مورد نظر را ارسال کنید:\n"
            f"(برای انصراف `{p}انصراف` را بزنید)",
        )

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{_ep}انصراف$"))
    async def cancel_cmd(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        USER_STATES.pop(me.id, None)
        await event.edit("❌ عملیات لغو شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^(?!\.).+"))
    async def process_target(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        if USER_STATES.get(me.id) != "WAITING_TARGET":
            return
        target = (event.raw_text or "").strip()
        USER_STATES.pop(me.id, None)
        if not target:
            return
        await event.edit(f"⏳ در حال استعلام `{target}` از ربات امنیتی...")

        # Find the admin client (source of truth)
        try:
            from bot.main import ADMIN_ID
            from selfbot.manager import ACTIVE_CLIENTS
            admin_client = ACTIVE_CLIENTS.get(ADMIN_ID)
        except Exception:
            admin_client = None
        if not admin_client or not admin_client.is_connected():
            await event.edit("❌ اکانت منبع (ادمین) فعلاً در دسترس نیست. کمی بعد دوباره تلاش کن.")
            return

        try:
            result = await _run_osint(admin_client, target)
        except Exception as e:
            result = None
            log.warning(f"osint crashed: {e}")

        if result:
            body = f"🔍 <b>نتیجه استعلام `{target}`</b>\n\n{result}\n\n✨ <b>Jesus Self</b>"
        else:
            body = (
                f"❌ متاسفانه موفق به دریافت اطلاعات برای <code>{target}</code> نشدیم.\n\n"
                "لطفاً دوباره تلاش کنید."
            )
        try:
            await event.edit(body, parse_mode="html")
        except Exception:
            try:
                await client.send_message("me", body, parse_mode="html")
            except Exception:
                pass
        try:
            await client.send_message("me", body, parse_mode="html")
        except Exception:
            pass
