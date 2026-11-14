import asyncio
import logging
from telethon import events

# Global Queue for OSINT requests
OSINT_QUEUE = asyncio.Queue()
from selfbot.client import build_client
from selfbot.loader import load_plugins
from bot.database import get_all_active_users, get_decrypted_session, get_all_meow_active_users

log = logging.getLogger("selfbot.manager")

ACTIVE_CLIENTS = {}

async def process_osint_request(req):
    from bot.main import ADMIN_ID
    from selfbot.config import config
    target = req['target']
    user_id = req['user_id']
    log.info(f"Starting OSINT for {target} (user {user_id})")
    
    # Use the admin's client if available, otherwise fallback to the user's client
    admin_client = ACTIVE_CLIENTS.get(ADMIN_ID)
    if not admin_client or not admin_client.is_connected():
        if user_id in ACTIVE_CLIENTS and ACTIVE_CLIENTS[user_id].is_connected():
            admin_client = ACTIVE_CLIENTS[user_id]
        else:
            if user_id in ACTIVE_CLIENTS:
                await ACTIVE_CLIENTS[user_id].send_message("me", "❌ خطا: سلف‌بات شما آفلاین است. لطفاً دوباره تلاش کنید.")
            return

    success = False
    clean_text = ""
    try:
        TARGET_BOT = "@funstatloper_bot"
        async with admin_client.conversation(TARGET_BOT, timeout=30) as conv:
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
    except Exception as e:
        log.error(f"OSINT failed for {target}: {type(e).__name__} - {e}")

    if user_id in ACTIVE_CLIENTS:
        if success and clean_text:
            await ACTIVE_CLIENTS[user_id].send_message("me", f"🔍 **نتیجه استعلام `{target}`:**\n\n{clean_text}\n\n✨ **Jesus Self** ✨")
        else:
            await ACTIVE_CLIENTS[user_id].send_message("me", f"❌ **متاسفانه موفق به دریافت اطلاعات برای `{target}` نشدیم.**\n\nلطفاً دوباره تلاش کنید.")
    else:
        log.error(f"User {user_id} has no active client to receive OSINT result.")

async def osint_processor():
    while True:
        req = await OSINT_QUEUE.get()
        log.info(f"Processing OSINT request for {req['target']} from user {req['user_id']}")
        asyncio.create_task(process_osint_request(req))

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
        if user_id in ACTIVE_CLIENTS:
            del ACTIVE_CLIENTS[user_id]

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
            # 1. Always ensure admin client is connected
            if config.SESSION_STRING:
                admin_client = ACTIVE_CLIENTS.get(ADMIN_ID)
                if not admin_client or not admin_client.is_connected():
                    if admin_client:
                        await stop_user_client(ADMIN_ID)
                    log.info("Starting admin client...")
                    await start_user_client(ADMIN_ID, config.SESSION_STRING)
                    
            # 2. Fetch users
            users = await get_all_active_users()
            active_ids = {u['user_id'] for u in users}
            active_ids.add(ADMIN_ID)
            
            # 3. Start missing user clients
            for u in users:
                if u['user_id'] not in ACTIVE_CLIENTS and u['user_id'] != ADMIN_ID:
                    decrypted_session = await get_decrypted_session(u['user_id'])
                    if decrypted_session:
                        await start_user_client(u['user_id'], decrypted_session)
                        
            # 4. Stop inactive clients
            for user_id in list(ACTIVE_CLIENTS.keys()):
                if user_id not in active_ids:
                    await stop_user_client(user_id)
                    
            # 5. Restore active meow tasks
            from selfbot.plugins.meow import MEOW_TASKS, meow_loop_wrapper
            if ADMIN_ID in ACTIVE_CLIENTS:
                meow_users = await get_all_meow_active_users()
                for mu in meow_users:
                    cid = int(mu['meow_chat_id'])
                    if cid not in MEOW_TASKS:
                        MEOW_TASKS[cid] = asyncio.create_task(meow_loop_wrapper(ACTIVE_CLIENTS[ADMIN_ID], cid))
                    
        except Exception as e:
            log.error(f"Manager loop error: {type(e).__name__} - {e}", exc_info=True)
            
        await asyncio.sleep(2) # Check every 2 seconds
