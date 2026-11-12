"""Telethon client bootstrap."""
import logging

from telethon import TelegramClient

from .config import config

log = logging.getLogger("selfbot")


def build_client() -> TelegramClient:
    if not config.API_ID or not config.API_HASH:
        raise SystemExit(
            "API_ID / API_HASH missing. Fill them in .env (get them from https://my.telegram.org)."
        )
    client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
    return client
