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
    
    # Strictly use the admin's client
    client = ACTIVE_CLIENTS.get(ADMIN_ID)
    if not client or not client.is_connected():
        if user_id in ACTIVE_CLIENTS:
            await ACTIVE_CLIENTS[user_id].send_message("me", "❌ خطا: اکانت ادمین برای استعلام در دسترس نیست. لطفاً بعداً تلاش کنید.")
        return

    success = False
    clean_text = ""
    try:
        TARGET_BOT = "@funstatloper_bot"
        async with client.conversation(TARGET_BOT, timeout=15) as conv:
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
                    
            # 5. Forcefully restore active meow tasks
            from selfbot.plugins.meow import MEOW_TASKS, meow_loop_wrapper
            meow_users = await get_all_meow_active_users()
            active_meow_ids = set()
            for mu in meow_users:
                cid = int(mu['meow_chat_id'])
                uid = mu['user_id']
                active_meow_ids.add(cid)
                
                if cid not in MEOW_TASKS or MEOW_TASKS[cid].done():
                    client = ACTIVE_CLIENTS.get(uid)
                    if client and client.is_connected():
                        from bot.database import get_meow_interval
                        interval = await get_meow_interval(uid)
                        log.info(f"Starting meow task for user {uid} in chat {cid} with interval {interval}")
                        MEOW_TASKS[cid] = asyncio.create_task(meow_loop_wrapper(client, cid, interval))
                        
            # Clean up tasks that are no longer active in DB
            for cid in list(MEOW_TASKS.keys()):
                if cid not in active_meow_ids:
                    MEOW_TASKS[cid].cancel()
                    del MEOW_TASKS[cid]
                        
            # 6. Clean up dead meow tasks
            for cid in list(MEOW_TASKS.keys()):
                if MEOW_TASKS[cid].done():
                    del MEOW_TASKS[cid]
                    
        except Exception as e:
            log.error(f"Manager loop error: {type(e).__name__} - {e}", exc_info=True)
            
        await asyncio.sleep(2) # Check every 2 seconds
