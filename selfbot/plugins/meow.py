"""Meow plugin: Automatically sends 'میو' in the target chat with detected cooldown."""
import asyncio
import re
from telethon import events
from selfbot.config import config

MEOW_TASKS = {}

async def meow_loop_wrapper(client, chat_id, interval_str):
    # Parse M:SS strictly from user's setting
    try:
        parts = interval_str.strip().split(':')
        cooldown = (int(parts[0]) * 60) + int(parts[1])
    except Exception as e:
        print(f"[MEOW] Invalid interval '{interval_str}', defaulting to 4:10. Error: {e}")
        cooldown = 250 # Fallback to 4:10 only if parsing fails
        
    while True:
        try:
            while not client.is_connected():
                await asyncio.sleep(2)
                
            try:
                await client.send_message(chat_id, "میو")
            except Exception as e:
                print(f"[MEOW] Send error: {e}")
                await asyncio.sleep(5)
                continue
                
            await asyncio.sleep(cooldown)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[MEOW ERROR] {e}")
            await asyncio.sleep(2)

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}تنظیم زمان میویی (\d+:\d+)$"))
    async def set_meow_time(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        interval = event.pattern_match.group(1).strip()
        from bot.database import set_meow_interval
        await set_meow_interval(me.id, interval)
        await event.edit(f"✅ زمان میو کردن شما روی **{interval}** (دقیقه:ثانیه) تنظیم شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}تنظیم میویی$"))
    async def set_meow_target(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        chat_id = event.chat_id
        chat = await event.get_chat()
        chat_title = getattr(chat, 'title', 'چت خصوصی')
        
        from bot.database import set_meow_target_db
        await set_meow_target_db(me.id, str(chat_id), chat_title)
        
        await event.edit(f"✅ چت **{chat_title}** به عنوان مقصد میو کردن تنظیم شد.\n\nحالا برای شروع، دستور `.میو روشن` را بزنید.", parse_mode="md")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}میو روشن$"))
    async def start_meow(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        from bot.database import get_meow_target_db, set_meow_active, get_meow_interval
        
        target = await get_meow_target_db(me.id)
        interval = await get_meow_interval(me.id)
        if not target or not target.get('chat_id'):
            await event.edit("⚠️ **خطا:** لطفاً ابتدا چت مقصد را با دستور `.تنظیم میویی` مشخص کنید.")
            return
            
        chat_id = int(target['chat_id'])
        
        if chat_id in MEOW_TASKS:
            MEOW_TASKS[chat_id].cancel()
            del MEOW_TASKS[chat_id]
            
        await event.edit(f"✅ شروع مجدد میو کردن در چت **{target['chat_title']}** با تایم **{interval}**...")
        
        MEOW_TASKS[chat_id] = asyncio.create_task(meow_loop_wrapper(client, chat_id, interval))
        await set_meow_active(me.id, 1)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}میو خاموش$"))
    async def stop_meow(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        from bot.database import set_meow_active
        
        chat_id = event.chat_id
        if chat_id in MEOW_TASKS:
            MEOW_TASKS[chat_id].cancel()
            del MEOW_TASKS[chat_id]
            await set_meow_active(me.id, 0)
            await event.edit("❌ میو کردن در این چت متوقف شد.")
        else:
            await set_meow_active(me.id, 0)
            await event.edit("⚠️ میو کردن در این چت روشن نیست.")
