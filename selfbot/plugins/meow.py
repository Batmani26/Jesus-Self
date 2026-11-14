"""Meow plugin: Automatically sends 'میو' in the target chat with detected cooldown."""
import asyncio
import re
from telethon import events
from selfbot.config import config

MEOW_TASKS = {}

async def meow_loop_wrapper(client, chat_id):
    cooldown = 250 # Default initial cooldown
    
    while True:
        try:
            # Block until the client is connected
            while not client.is_connected():
                await asyncio.sleep(2)
                
            try:
                msg = await client.send_message(chat_id, "میو")
            except Exception as e:
                print(f"[MEOW] Send error: {e}")
                await asyncio.sleep(5)
                continue
                
            # Attempt to read the cooldown from the bot's reply
            await asyncio.sleep(3)
            try:
                updated_msg = await client.get_messages(chat_id, ids=msg.id)
                if updated_msg and updated_msg.reply_to_msg_id:
                    reply = await updated_msg.get_reply_message()
                    if reply and reply.text:
                        match_mmss = re.search(r'(\d+):(\d+)', reply.text)
                        if match_mmss:
                            minutes = int(match_mmss.group(1))
                            seconds = int(match_mmss.group(2))
                            cooldown = (minutes * 60) + seconds + 2
            except Exception as e:
                print(f"[MEOW] Read error: {e}")
                
            await asyncio.sleep(cooldown)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[MEOW ERROR] {e}")
            await asyncio.sleep(2)

def register(client) -> None:
    p = config.PREFIX

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
        from bot.database import get_meow_target_db, set_meow_active
        
        target = await get_meow_target_db(me.id)
        if not target or not target.get('chat_id'):
            await event.edit("⚠️ **خطا:** لطفاً ابتدا چت مقصد را با دستور `.تنظیم میویی` مشخص کنید.")
            return
            
        chat_id = int(target['chat_id'])
        
        if chat_id in MEOW_TASKS:
            MEOW_TASKS[chat_id].cancel()
            del MEOW_TASKS[chat_id]
            
        await event.edit(f"✅ شروع مجدد میو کردن در چت **{target['chat_title']}**...")
        
        MEOW_TASKS[chat_id] = asyncio.create_task(meow_loop_wrapper(client, chat_id))
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
