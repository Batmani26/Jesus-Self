"""Telethon client bootstrap."""
import logging

from telethon import TelegramClient
from telethon.sessions import StringSession

from .config import config

log = logging.getLogger("selfbot")


def build_client(session_string=None) -> TelegramClient:
    if not config.API_ID or not config.API_HASH:
        raise SystemExit(
            "API_ID / API_HASH missing. Fill them in .env (get them from https://my.telegram.org)."
        )
    proxy = config.proxy_tuple()
    kwargs = {"connection_retries": 10, "retry_delay": 3, "request_retries": 10}
    if proxy:
        kwargs["proxy"] = proxy
        log.info("Using Telegram proxy: %s://%s:%s", proxy[0], proxy[1], proxy[2])
    if session_string:
        client = TelegramClient(StringSession(session_string), config.API_ID, config.API_HASH, **kwargs)
    elif config.SESSION_STRING:
        client = TelegramClient(StringSession(config.SESSION_STRING), config.API_ID, config.API_HASH, **kwargs)
    else:
        client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH, **kwargs)
    return client
