"""Starts both the Management Bot and the Selfbot in the same process for Render."""
import asyncio
import logging
from keep_alive import keep_alive

from bot.main import dp, bot
from main import run as selfbot_run

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
log = logging.getLogger("start_all")

async def run_all():
    keep_alive()
    log.info("Starting Management Bot and Selfbot...")
    await asyncio.gather(
        dp.start_polling(bot),
        selfbot_run()
    )

if __name__ == "__main__":
    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        log.info("Stopped.")
