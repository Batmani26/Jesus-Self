import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

import os
from dotenv import load_dotenv
load_dotenv()

# Read API credentials from environment (never hardcode secrets)
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
if not API_ID or not API_HASH:
    raise RuntimeError("API_ID / API_HASH missing. Fill them in .env")

async def send_code(phone):
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    try:
        sent_code = await client.send_code_request(phone)
        return client, sent_code.phone_code_hash, None
    except Exception as e:
        return None, None, str(e)

async def verify_code(client, phone, code, phone_code_hash):
    try:
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        return True, None
    except SessionPasswordNeededError:
        return False, '2FA_NEEDED'
    except Exception as e:
        return False, str(e)

async def verify_password(client, password):
    try:
        await client.sign_in(password=password)
        return True, None
    except Exception as e:
        return False, str(e)
