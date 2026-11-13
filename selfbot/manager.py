import asyncio
import logging
from telethon import events
from selfbot.client import build_client
from selfbot.loader import load_plugins
from bot.database import get_all_active_users

log = logging.getLogger("selfbot.manager")

ACTIVE_CLIENTS = {}

async def start_user_client(user_id, session_string):
    if user_id in ACTIVE_CLIENTS:
        return
    try:
        client = build_client(session_string)
        await client.start()
        load_plugins(client)
        ACTIVE_CLIENTS[user_id] = client
        log.info(f"Started selfbot for user {user_id}")
        asyncio.create_task(client.run_until_disconnected())
    except Exception as e:
        log.error(f"Failed to start selfbot for user {user_id}: {e}")

async def stop_user_client(user_id):
    if user_id in ACTIVE_CLIENTS:
        client = ACTIVE_CLIENTS[user_id]
        await client.disconnect()
        del ACTIVE_CLIENTS[user_id]
        log.info(f"Stopped selfbot for user {user_id}")

from selfbot.config import config
from bot.main import ADMIN_ID

async def manager_loop():
    while True:
        try:
            users = await get_all_active_users()
            active_ids = {u['user_id'] for u in users}
            # Ensure admin is always active if session string is available
            if config.SESSION_STRING and ADMIN_ID not in active_ids:
                active_ids.add(ADMIN_ID)
            
            for u in users:
                if u['user_id'] not in ACTIVE_CLIENTS and u['session_string']:
                    await start_user_client(u['user_id'], u['session_string'])
                    
            for user_id in list(ACTIVE_CLIENTS.keys()):
                if user_id not in active_ids:
                    await stop_user_client(user_id)
                    
        except Exception as e:
            log.error(f"Manager loop error: {e}")
        await asyncio.sleep(60)
