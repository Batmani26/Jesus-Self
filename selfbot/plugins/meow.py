"""Meow plugin: Automatically sends 'میو' in the target chat with detected cooldown."""
import asyncio
import re
from telethon import events
from selfbot.config import config

MEOW_TASKS = {}

async def meow_loop_wrapper(client, chat_id):
    while True:
        try:
            msg = await client.send_message(chat_id, "میو")
            print(f"[MEOW] Sent 'میو' to {chat_id}")
            
            cooldown = 60 # Default if parsing fails
            # Wait for the bot to respond
            for _ in range(5):
                await asyncio.sleep(2)
                messages = await client.get_messages(chat_id, limit=3)
                found = False
                for m in messages:
                    if m.text and ("بعد از" in m.text or "باید" in m.text):
                        match_mmss = re.search(r'(\d+):(\d+)', m.text)
                        if match_mmss:
                            minutes = int(match_mmss.group(1))
                            seconds = int(match_mmss.group(2))
                            cooldown = (minutes * 60) + seconds + 1 # 1s buffer
                            found = True
                        else:
                            match_words = re.search(r'(\d+)\s*(ثانیه|دقیقه)', m.text)
                            if match_words:
                                val = int(match_words.group(1))
                                if "دقیقه" in match_words.group(2):
                                    val *= 60
                                cooldown = val + 1
                                found = True
                        break
                if found:
                    break
            
            print(f"[MEOW] Waiting for {cooldown} seconds...")
            await asyncio.sleep(cooldown)
        except Exception as e:
            print(f"[MEOW ERROR] {e}")
            await asyncio.sleep(10)

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}تنظیم میویی$"))
    async def set_meow_target(event: events.NewMessage.Event) -> None:
        chat_id = event.chat_id
        chat = await event.get_chat()
        chat_title = getattr(chat, 'title', 'چت خصوصی')
        
        from bot.database import set_meow_target_db
        from bot.main import ADMIN_ID
        await set_meow_target_db(ADMIN_ID, str(chat_id), chat_title)
        
        await event.edit(f"✅ چت **{chat_title}** به عنوان مقصد میو کردن تنظیم شد.\n\nحالا برای شروع، دستور `.میو روشن` را بزنید.", parse_mode="md")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}میو روشن$"))
    async def start_meow(event: events.NewMessage.Event) -> None:
        from bot.database import get_meow_target_db
        from bot.main import ADMIN_ID
        
        target = await get_meow_target_db(ADMIN_ID)
        if not target or not target.get('chat_id'):
            await event.edit("⚠️ **خطا:** لطفاً ابتدا چت مقصد را با دستور `.تنظیم میویی` مشخص کنید.")
            return
            
        chat_id = int(target['chat_id'])
        
        # If a task exists, cancel it to start a fresh one
        if chat_id in MEOW_TASKS:
            MEOW_TASKS[chat_id].cancel()
            del MEOW_TASKS[chat_id]
            
        await event.edit(f"✅ شروع مجدد میو کردن در چت **{target['chat_title']}**...")
        
        MEOW_TASKS[chat_id] = asyncio.create_task(meow_loop_wrapper(client, chat_id))
        from bot.database import set_meow_active
        await set_meow_active(ADMIN_ID, 1)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}میو خاموش$"))
    async def stop_meow(event: events.NewMessage.Event) -> None:
        from bot.main import ADMIN_ID
        from bot.database import set_meow_active
        
        chat_id = event.chat_id
        if chat_id in MEOW_TASKS:
            MEOW_TASKS[chat_id].cancel()
            del MEOW_TASKS[chat_id]
            await set_meow_active(ADMIN_ID, 0)
            await event.edit("❌ میو کردن در این چت متوقف شد.")
        else:
            await set_meow_active(ADMIN_ID, 0)
            await event.edit("⚠️ میو کردن در این چت روشن نیست.")
