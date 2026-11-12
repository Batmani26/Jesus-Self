"""Starts both the Management Bot and the Selfbot in the same process for Render."""
import asyncio
import logging
from aiohttp import web
from bot.main import dp, bot
from main import run as selfbot_run

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
log = logging.getLogger("start_all")

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
    log.info("Starting Management Bot and Selfbot...")
    try:
        await asyncio.gather(
            dp.start_polling(bot),
            selfbot_run(),
            start_web_server()
        )
    except Exception as e:
        log.error(f"Crash in run_all: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        log.info("Stopped.")
