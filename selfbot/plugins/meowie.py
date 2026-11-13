"""Meowie cheat plugin: Spams the bot's inline button until a win is achieved."""
import asyncio
from telethon import events, functions
from telethon.tl.types import InputMediaDice
from selfbot.config import config

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}میویی(?:\s+([1-6]))?$"))
    async def meowie_cheat(event: events.NewMessage.Event) -> None:
        # Find the bot's message with the button
        if not event.reply_to_msg_id:
            await event.edit("⚠️ لطفاً این دستور را در ریپلای به پیام ربات میویی بفرستید.")
            return
            
        bot_msg = await event.get_reply_message()
        if not bot_msg or not bot_msg.reply_markup:
            # Search recent messages for the bot's button
            bot = await event.client.get_entity('@MeowieQVBot')
            messages = await client.get_messages(event.chat_id, limit=15)
            for msg in messages:
                if msg.from_id == bot.id and msg.reply_markup:
                    bot_msg = msg
                    break
            
            if not bot_msg or not bot_msg.reply_markup:
                await event.edit("⚠️ پیام ربات با دکمه شیشه‌ای پیدا نشد.")
                return
            
        # Detect the desired number
        desired = None
        if event.pattern_match.group(1):
            desired = int(event.pattern_match.group(1))
        else:
            # Try to find the number in the replied message or previous messages
            import re
            msg_text = bot_msg.text or ""
            match = re.search(r'\b([1-6])\b', msg_text)
            if match:
                desired = int(match.group(1))
            else:
                # Check the user's message that replied to the bot
                if bot_msg.reply_to_msg_id:
                    user_msg = await client.get_messages(event.chat_id, ids=bot_msg.reply_to_msg_id)
                    if user_msg and user_msg.text:
                        match = re.search(r'\b([1-6])\b', user_msg.text)
                        if match:
                            desired = int(match.group(1))
                            
        if not desired:
            await event.edit("⚠️ عدد مورد نظر پیدا نشد. لطفاً به این صورت بزنید: `.میویی 6`")
            return
            
        await event.edit("⏳ در حال تلاش برای برنده شدن...")
        bot = await event.client.get_entity('@MeowieQVBot')
        for _ in range(10):
            try:
                # Use msg.click() which automatically handles the callback query
                await bot_msg.click()
                
                # Wait for the bot's response
                await asyncio.sleep(2)
                messages = await client.get_messages(event.chat_id, limit=5)
                for msg in messages:
                    if msg.from_id == bot.id and msg.media:
                        if hasattr(msg.media, 'value') and msg.media.value == desired:
                            await event.delete()
                            return
            except Exception as e:
                print(f"Meowie click error: {e}")
                await asyncio.sleep(1)
                
        await event.edit("❌ متاسفانه موفق نشدیم.")
