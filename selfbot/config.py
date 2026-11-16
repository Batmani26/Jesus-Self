"""Configuration loader for the selfbot.
Reads secrets from .env so nothing sensitive lives in the repo.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


class Config:
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    SESSION_NAME = os.getenv("SESSION_NAME", "selfbot_session")
    SESSION_STRING = os.getenv("SESSION_STRING", None)

    # Command prefix, e.g. ".help"
    PREFIX = os.getenv("PREFIX", ".")

    # Feature toggles
    ENABLE_ANTI_DELETE = os.getenv("ENABLE_ANTI_DELETE", "true").lower() == "true"
    ENABLE_TIMED_SAVER = os.getenv("ENABLE_TIMED_SAVER", "true").lower() == "true"

    # Where saved media goes
    DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))

    # Optional proxy for Telegram (needed in Iran). Format:
    #   socks5://user:pass@host:port  or  http://host:port  or  MTProxy
    TG_PROXY = os.getenv("TG_PROXY", "").strip() or None

    def proxy_tuple(self):
        """Return (scheme, host, port, rdns, username, password) for Telethon, or None."""
        p = self.TG_PROXY
        if not p:
            return None
        try:
            from urllib.parse import urlparse
            u = urlparse(p)
            if not u.hostname or not u.port:
                return None
            return (u.scheme, u.hostname, u.port, True, u.username, u.password)
        except Exception:
            return None


config = Config()
