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
            
        try:
            from telethon import functions, types
            # Check if we have a conversation with the target bot
            TARGET_BOT = "@funstatloper_bot"
            async with admin_client.conversation(TARGET_BOT, timeout=60) as conv:
                sent_msg = await conv.send_message(target)
                await sent_msg.delete()
                
                import re
                while True:
                    response = await conv.get_response()
                    txt = response.text
                    # Ignore messages containing hourglass or the word "for data"
                    clean_txt = re.sub(r'[^\x00-\x7F]+', '', txt).lower()
                    if "⏳" in txt or "for da" in clean_txt or "looking" in clean_txt or "loading" in clean_txt or "searching" in clean_txt or len(txt) < 50:
                        await response.delete()
                        continue
                    break
                await response.delete()
                clean_text = response.text.split("Sτiсқеrs℮tѕ:")[0].strip()
                
            # Send to the requesting user
            if user_id in ACTIVE_CLIENTS:
                await ACTIVE_CLIENTS[user_id].send_message("me", f"🔍 **نتیجه استعلام `{target}`:**\n\n{clean_text}\n\n✨ **Jesus Self** ✨")
        except asyncio.TimeoutError:
            log.error(f"OSINT Timeout for {target}")
            if user_id in ACTIVE_CLIENTS:
                await ACTIVE_CLIENTS[user_id].send_message("me", f"❌ **خطا:** ربات استعلام‌کننده پاسخ نداد. لطفاً دوباره تلاش کنید.")
        except Exception as e:
            log.error(f"OSINT processor error: {e}")
            if user_id in ACTIVE_CLIENTS:
                await ACTIVE_CLIENTS[user_id].send_message("me", f"❌ **خطا در استعلام:**\n`{e}`")

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
    while True:
        try:
            users = await get_all_active_users()
            active_ids = {u['user_id'] for u in users}
            # Ensure admin is always active if session string is available
            from bot.main import ADMIN_ID
            from selfbot.config import config
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
        await asyncio.sleep(10)
