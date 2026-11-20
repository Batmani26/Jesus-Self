"""Starts both the Management Bot and the Selfbot in the same process for Render."""
import asyncio
import logging
from aiohttp import web

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
log = logging.getLogger("start_all")
from bot.main import dp, bot, panel_updater_loop
from bot.database import init_db, get_all_active_users, deduct_yaqoot, deactivate_user
from selfbot.manager import manager_loop, osint_processor
from aiogram import Bot
from bot.main import BOT_TOKEN

import datetime

async def billing_loop():
    while True:
        await asyncio.sleep(60) # Check every minute
        try:
            users = await get_all_active_users()
            now = datetime.datetime.now(datetime.timezone.utc)
            for u in users:
                uid = u['user_id']
                bal = u['yaqoot_balance']
                last_ded = u['last_deduction']
                if last_ded is None:
                    last_ded = now
                if isinstance(last_ded, datetime.datetime):
                    if last_ded.tzinfo is None:
                        last_ded = last_ded.replace(tzinfo=datetime.timezone.utc)
                
                elapsed = (now - last_ded).total_seconds()
                if elapsed >= 3600:
                    new_bal = bal - 2
                    if new_bal <= 0:
                        await deduct_yaqoot(uid, bal)
                        await deactivate_user(uid)
                        try:
                            b = Bot(token=BOT_TOKEN)
                            await b.send_message(uid, "❌ **موجودی یاقوت شما به پایان رسید.**\n\nسلف‌بات شما غیرفعال شد. لطفاً حساب خود را شارژ کنید.", parse_mode="Markdown")
                            await b.session.close()
                        except: pass
                    else:
                        await deduct_yaqoot(uid, 2)
                        if new_bal < 48:
                            try:
                                b = Bot(token=BOT_TOKEN)
                                await b.send_message(uid, f"⚠️ **هشدار موجودی**\n\nموجودی یاقوت شما به **{new_bal}** رسیده است.\nکمتر از ۲۴ ساعت تا پایان موجودی شما باقی مانده است. لطفاً شارژ کنید.", parse_mode="Markdown")
                                await b.session.close()
                            except: pass
        except Exception as e:
            log.error(f"Billing loop error: {e}")

async def start_web_server():
    async def handle(request):
        return web.Response(text="Jesus Self Bot is alive!")
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    import os
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()
    log.info("Web server started on port 8080")

async def start_web_server_guarded():
    """Bind the web server exactly once; never retry binding to avoid EADDRINUSE."""
    try:
        await start_web_server()
    except OSError as e:
        log.warning(f"Web server bind skipped: {e}")
    # Keep this task alive (port stays bound by the running site)
    while True:
        await asyncio.sleep(3600)

async def run_all():
    import os as _os
    # ROLE controls what this instance does.
    #   "all"      → management bot + admin selfbot + user selfbots + billing (single-host setup)
    #   "manage"   → management bot + admin selfbot + billing (no user selfbots)
    #   "selfonly" → ONLY user selfbots (no aiogram polling, no billing) — for a 2nd host
    ROLE = (_os.getenv("ROLE", "all") or "all").strip().lower()
    if ROLE not in ("all", "manage", "selfonly"):
        ROLE = "all"
    log.info(f"Host role: {ROLE}")

    log.info("Connecting to database...")
    await init_db()

    # Auto-detect a working proxy for Telegram (no-op on Render/foreign servers)
    try:
        from selfbot.auto_proxy import ensure_proxy_env, proxy_refresh_loop
        best = await ensure_proxy_env()
        log.info(f"Auto-proxy resolved: {best or 'direct (no proxy needed)'}")
        asyncio.create_task(proxy_refresh_loop(600))
    except Exception as e:
        log.warning(f"Auto-proxy detection failed: {e}")

    log.info("Starting Management Bot and Selfbot...")
    if ROLE in ("all", "manage"):
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            log.info("Webhook cleared, pending updates dropped")
        except Exception as exc:
            log.warning(f"Could not clear webhook: {exc}")
    else:
        log.info("selfonly role: skipping aiogram webhook clear / polling / billing")
    
    async def safe_loop(loop_func, name):
        while True:
            try:
                await loop_func()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in {name}: {e}", exc_info=True)
                await asyncio.sleep(5)
                
    async def polling_forever():
        """Auto-restart aiogram polling. Handles TelegramConflictError gracefully (another instance
        still terminating after deploy)."""
        conflict_attempts = 0
        while True:
            try:
                await bot.delete_webhook(drop_pending_updates=True)
            except Exception:
                pass
            try:
                await dp.start_polling(
                    bot,
                    allowed_updates=["message", "callback_query", "inline_query", "chosen_inline_result", "my_chat_member", "chat_member"],
                    handle_signals=False,
                )
                conflict_attempts = 0
            except asyncio.CancelledError:
                raise
            except Exception as e:
                emsg = str(e).lower()
                if "conflict" in emsg or "terminated by other getupdates" in emsg:
                    conflict_attempts += 1
                    wait = min(30, 3 * conflict_attempts)
                    log.warning(f"TelegramConflictError: another instance is polling the same bot. Retry in {wait}s (attempt {conflict_attempts}). Only one instance should run.")
                    await asyncio.sleep(wait)
                    continue
                log.error(f"Polling crashed: {e}. Restarting in 10s...", exc_info=True)
                await asyncio.sleep(10)

    tasks = [
        start_web_server_guarded(),
        safe_loop(manager_loop, "manager_loop"),
    ]
    if ROLE in ("all", "manage"):
        tasks.append(polling_forever())
        tasks.append(safe_loop(panel_updater_loop, "panel_updater_loop"))
        tasks.append(safe_loop(billing_loop, "billing_loop"))
        # osint uses the admin client; only meaningful on the management host
        tasks.append(safe_loop(osint_processor, "osint_processor"))
    else:
        log.info("selfonly role: skipping polling/billing/panel/osint loops")

    await asyncio.gather(*tasks, return_exceptions=True)
    # Top-level keepalive (should never reach here if gather works)
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        log.info("Stopped.")
