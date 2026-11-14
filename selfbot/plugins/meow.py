"""Meow plugin: Automatically sends 'میو' in the target chat with detected cooldown."""
import asyncio
import re
from telethon import events
from selfbot.config import config

MEOW_TASKS = {}

async def meow_loop_wrapper(client, chat_id, interval_str, immediate=True):
    if not interval_str:
        print(f"[MEOW] No interval for {chat_id}")
        return
    try:
        parts = interval_str.strip().split(chr(58))
        cooldown = int(parts[0]) * 60 + int(parts[1])
        if cooldown <= 0:
            raise ValueError(chr(99)+chr(111)+chr(111)+chr(108))
    except Exception as e:
        print(f"[MEOW] Invalid interval {interval_str}: {e}")
        return
    loop = asyncio.get_event_loop()
    next_send = loop.time() if immediate else loop.time() + cooldown
    print(f"[MEOW] Start {chat_id} cooldown={cooldown}s")
    while True:
        try:
            now = loop.time()
            delay = next_send - now
            if delay > 0:
                await asyncio.sleep(delay)
            while not client.is_connected():
                await asyncio.sleep(1)
            try:
                await client.send_message(chat_id, chr(1605)+chr(1740)+chr(1608))
                print(f"[MEOW] Sent to {chat_id}")
            except Exception as e:
                print(f"[MEOW] Send error {e}")
                next_send += cooldown
                continue
            next_send += cooldown
            if next_send < loop.time():
                next_send = loop.time()
        except asyncio.CancelledError:
            print(f"[MEOW] Task {chat_id} cancelled")
            break
        except Exception as e:
            print(f"[MEOW ERROR] {e}")
            next_send = loop.time() + cooldown

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
            
        if not interval:
            await event.edit("⚠️ **خطا:** لطفاً ابتدا زمان میو کردن خود را با دستور `.تنظیم زمان میویی 4:20` (به عنوان مثال) تنظیم کنید.")
            return
            
        chat_id = int(target['chat_id'])
        
        if chat_id in MEOW_TASKS:
            await event.edit("⚠️ میو کردن در این چت از قبل روشن است.")
            return
            
        await event.edit(f"✅ شروع میو کردن در چت **{target['chat_title']}** با تایم **{interval}**...")
        
        for cid in list(MEOW_TASKS.keys()):
            MEOW_TASKS[cid].cancel()
            del MEOW_TASKS[cid]
        MEOW_TASKS[chat_id] = asyncio.create_task(meow_loop_wrapper(client, chat_id, interval))
        await set_meow_active(me.id, 1)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{p}میو خاموش$"))
    async def stop_meow(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        from bot.database import set_meow_active, get_meow_target_db
        stopped = False
        for cid in list(MEOW_TASKS.keys()):
            MEOW_TASKS[cid].cancel()
            del MEOW_TASKS[cid]
            stopped = True
        await set_meow_active(me.id, 0)
        if stopped:
            await event.edit("✕ میو خاموش شد")
        else:
            await event.edit("⚠ میو روشن نیست")
