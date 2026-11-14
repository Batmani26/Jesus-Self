import asyncio
import logging
from telethon import events

# Global Queue for OSINT requests
OSINT_QUEUE = asyncio.Queue()
from selfbot.client import build_client
from selfbot.loader import load_plugins
from bot.database import get_all_active_users

log = logging.getLogger("selfbot.manager")

ACTIVE_CLIENTS = {}

async def osint_processor():
    from bot.main import ADMIN_ID
    from selfbot.config import config
    while True:
        req = await OSINT_QUEUE.get()
        target = req['target']
        user_id = req['user_id']
        log.info(f"Processing OSINT request for {target} from user {user_id}")
        asyncio.create_task(process_osint_request(req))
        
        # Ensure admin client is running
        from selfbot.config import config
        admin_client = ACTIVE_CLIENTS.get(ADMIN_ID)
        if admin_client:
            try:
                await admin_client.get_me()
            except Exception:
                admin_client = None
                
        if not admin_client:
            if config.SESSION_STRING:
                try:
                    client = build_client(config.SESSION_STRING)
                    await client.start()
                    load_plugins(client)
                    ACTIVE_CLIENTS[ADMIN_ID] = client
                    asyncio.create_task(client.run_until_disconnected())
                    admin_client = client
                except Exception as e:
                    log.error(f"Failed to start admin client for OSINT: {e}")
                    if user_id in ACTIVE_CLIENTS:
                        await ACTIVE_CLIENTS[user_id].send_message("me", f"❌ خطا در پردازش استاک (عدم دسترسی به اکانت اصلی): {e}")
                    continue
            else:
                if user_id in ACTIVE_CLIENTS:
                    await ACTIVE_CLIENTS[user_id].send_message("me", "❌ خطا: SESSION_STRING ادمین تنظیم نشده است.")
                continue
            
        success = False
        clean_text = ""
        for attempt in range(3):
            try:
                TARGET_BOT = "@funstatloper_bot"
                async with admin_client.conversation(TARGET_BOT, timeout=20) as conv:
                    sent_msg = await conv.send_message(target)
                    await sent_msg.delete()
                    
                    import re
                    while True:
                        response = await conv.get_response()
                        txt = response.text
                        clean_txt = re.sub(r'[^\x00-\x7F]+', '', txt).lower()
                        if "⏳" in txt or "for da" in clean_txt or "looking" in clean_txt or "loading" in clean_txt or "searching" in clean_txt or len(txt) < 50:
                            await response.delete()
                            continue
                        break
                    await response.delete()
                    clean_text = response.text.split("Sτiсқеrs℮tѕ:")[0].strip()
                    success = True
                    break
            except Exception as e:
                log.error(f"OSINT attempt {attempt+1} failed: {e}")
                # No sleep here to be faster

        if user_id in ACTIVE_CLIENTS:
            if success and clean_text:
                await ACTIVE_CLIENTS[user_id].send_message("me", f"🔍 **نتیجه استعلام `{target}`:**\n\n{clean_text}\n\n✨ **Jesus Self** ✨")
            else:
                await ACTIVE_CLIENTS[user_id].send_message("me", f"❌ **متاسفانه موفق به دریافت اطلاعات برای `{target}` نشدیم.**\n\nلطفاً دوباره تلاش کنید.")

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

async def manager_loop():
    from bot.main import ADMIN_ID
    from selfbot.config import config
    
    while True:
        try:
            users = await get_all_active_users()
            active_ids = {u['user_id'] for u in users}
            
            if config.SESSION_STRING and ADMIN_ID not in active_ids:
                active_ids.add(ADMIN_ID)
            
            # Check existing clients health and reconnect if needed
            for user_id, client in list(ACTIVE_CLIENTS.items()):
                try:
                    if not client.is_connected():
                        log.warning(f"Client for user {user_id} is disconnected, restarting...")
                        await stop_user_client(user_id)
                except Exception:
                    await stop_user_client(user_id)
            
            # Start missing clients concurrently
            tasks = []
            for u in users:
                if u['user_id'] not in ACTIVE_CLIENTS and u['session_string']:
                    tasks.append(start_user_client(u['user_id'], u['session_string']))
            if tasks:
                await asyncio.gather(*tasks)
                    
            # Ensure admin is running
            if config.SESSION_STRING and ADMIN_ID not in ACTIVE_CLIENTS:
                await start_user_client(ADMIN_ID, config.SESSION_STRING)
                    
            # Stop clients that are no longer active
            for user_id in list(ACTIVE_CLIENTS.keys()):
                if user_id not in active_ids:
                    await stop_user_client(user_id)
                    
        except Exception as e:
            log.error(f"Manager loop error: {e}")
        await asyncio.sleep(1) # Check every 1 second
