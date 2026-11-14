"""Fishing plugin: Automatically sends 'ماهی' in the target chat."""
import asyncio
import re
from telethon import events
from selfbot.config import config

FISHING_TASKS = {}

async def fishing_loop_wrapper(client, chat_id, interval_str):
    if not interval_str:
        return
    try:
        parts = interval_str.strip().split(':')
        cooldown = (int(parts[0]) * 60) + int(parts[1])
        if cooldown <= 0:
            return
    except Exception:
        return
        
    while True:
        try:
            while not client.is_connected():
                await asyncio.sleep(2)
                
            await client.send_message(chat_id, "ماهی")
            await asyncio.sleep(cooldown)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(2)

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern="^" + re.escape(p) + "تنظیم زمان ماهیگیری (\\d+:\\d+)$"))
    async def set_fishing_time(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        interval = event.pattern_match.group(1).strip()
        from bot.database import set_fishing_interval
        await set_fishing_interval(me.id, interval)
        await event.edit(f"✅ زمان ماهیگیری شما روی **{interval}** (دقیقه:ثانیه) تنظیم شد.")

    @client.on(events.NewMessage(outgoing=True, pattern="^" + re.escape(p) + "ماهیگیری روشن$"))
    async def start_fishing(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        from bot.database import get_meow_target_db, get_fishing_interval, set_fishing_active
        
        target = await get_meow_target_db(me.id)
        interval = await get_fishing_interval(me.id)
        if not target or not target.get('chat_id'):
            await event.edit("⚠️ **خطا:** لطفاً ابتدا چت مقصد را با دستور `.تنظیم میویی` مشخص کنید.")
            return
        if not interval:
            await event.edit("⚠️ **خطا:** لطفاً ابتدا زمان ماهیگیری خود را با دستور `.تنظیم زمان ماهیگیری 4:20` تنظیم کنید.")
            return
            
        chat_id = int(target['chat_id'])
        for cid in list(FISHING_TASKS.keys()):
            FISHING_TASKS[cid].cancel()
            del FISHING_TASKS[cid]
        if chat_id in FISHING_TASKS:
            await event.edit("⚠️ ماهیگیری در این چت از قبل روشن است.")
            return
            
        await event.edit(f"✅ شروع ماهیگیری در چت **{target['chat_title']}** با تایم **{interval}**...")
        FISHING_TASKS[chat_id] = asyncio.create_task(fishing_loop_wrapper(client, chat_id, interval))
        await set_fishing_active(me.id, 1)

    @client.on(events.NewMessage(outgoing=True, pattern="^" + re.escape(p) + "ماهیگیری خاموش$"))
    async def stop_fishing(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        from bot.database import set_fishing_active, get_meow_target_db
        _t = await get_meow_target_db(me.id)
        chat_id = int(_t[chr(39)+chr(99)+chr(104)+chr(97)+chr(116)+chr(95)+chr(105)+chr(100)+chr(39)]) if _t and _t.get(chr(39)+chr(99)+chr(104)+chr(97)+chr(116)+chr(95)+chr(105)+chr(100)+chr(39)) else event.chat_id
        if chat_id in FISHING_TASKS:
            FISHING_TASKS[chat_id].cancel()
            del FISHING_TASKS[chat_id]
            await set_fishing_active(me.id, 0)
            await event.edit("❌ ماهیگیری در این چت متوقف شد.")
        else:
            await set_fishing_active(me.id, 0)
            await event.edit("⚠️ ماهیگیری در این چت روشن نیست.")
