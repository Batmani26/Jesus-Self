"""SelfBot X entry point.

Usage:
    python main.py
"""
import asyncio
import logging
from keep_alive import keep_alive

from selfbot.client import build_client
from selfbot.config import config
from selfbot.loader import load_plugins

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("selfbot")


async def run() -> None:
    config.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    client = build_client()
    try:
        await client.start()
    except Exception as e:
        log.error(f"Selfbot failed to start (maybe no session?): {e}")
        return

    me = await client.get_me()
    log.info("Logged in as %s (id=%s)", me.first_name, me.id)

    plugins = load_plugins(client)
    log.info("Loaded %d plugin(s): %s", len(plugins), ", ".join(plugins) or "-")

    print(f"\n[OK] Jesus Self running with prefix '{config.PREFIX}'. Press Ctrl+C to stop.\n")
    await client.run_until_disconnected()


if __name__ == "__main__":
    keep_alive()
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("Stopped by user.")
