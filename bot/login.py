import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

# You can change these to your own API credentials. 2040 is a well-known public one.
API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'

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
