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
import asyncio

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
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    log.info("Web server started on port 8080")

async def run_all():
    log.info("Connecting to database...")
    await init_db()
    log.info("Starting Management Bot and Selfbot...")
    
    async def safe_loop(loop_func, name):
        while True:
            try:
                await loop_func()
            except Exception as e:
                log.error(f"Error in {name}: {e}", exc_info=True)
                await asyncio.sleep(5)
                # The loop_func itself has a while True, so if it throws, we restart it here.
                
    await asyncio.gather(
        dp.start_polling(bot),
        start_web_server(),
        safe_loop(manager_loop, "manager_loop"),
        safe_loop(osint_processor, "osint_processor"),
        safe_loop(billing_loop, "billing_loop"),
        safe_loop(panel_updater_loop, "panel_updater_loop")
    )

if __name__ == "__main__":
    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        log.info("Stopped.")
