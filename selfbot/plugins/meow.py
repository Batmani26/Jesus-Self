"""Meow plugin: Automatically sends 'میو' in the target chat with detected cooldown."""
import asyncio
import re
from telethon import events
from selfbot.config import config

MEOW_TASKS = {}

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}میو روشن$"))
    async def start_meow(event: events.NewMessage.Event) -> None:
        chat_id = event.chat_id
        if chat_id in MEOW_TASKS:
            await event.edit("⚠️ میو کردن در این چت از قبل روشن است.")
            return
            
        await event.edit("✅ این چت به عنوان چت مقصد انتخاب شد. شروع میو کردن...")
        
        async def meow_loop():
            while True:
                try:
                    msg = await client.send_message(chat_id, "میو")
                    await asyncio.sleep(1) # wait a bit for the bot to respond
                    
                    # Check for cooldown message
                    messages = await client.get_messages(chat_id, limit=5)
                    cooldown = 60 # default
                    for m in messages:
                        if m.reply_to_msg_id == msg.id and m.text:
                            # look for numbers in the response
                            match = re.search(r'(\d+)\s*(ثانیه|دقیقه)', m.text)
                            if match:
                                val = int(match.group(1))
                                if "دقیقه" in match.group(2):
                                    val *= 60
                                cooldown = val + 1 # add 1 second buffer
                            break
                            
                    await asyncio.sleep(cooldown)
                except Exception as e:
                    print(f"Meow error: {e}")
                    await asyncio.sleep(10)
                    
        MEOW_TASKS[chat_id] = asyncio.create_task(meow_loop())

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}میو خاموش$"))
    async def stop_meow(event: events.NewMessage.Event) -> None:
        chat_id = event.chat_id
        if chat_id in MEOW_TASKS:
            MEOW_TASKS[chat_id].cancel()
            del MEOW_TASKS[chat_id]
            await event.edit("❌ میو کردن در این چت متوقف شد.")
        else:
            await event.edit("⚠️ میو کردن در این چت روشن نیست.")
