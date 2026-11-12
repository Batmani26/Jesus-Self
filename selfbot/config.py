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


config = Config()
