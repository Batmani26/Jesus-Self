"""Meowie cheat plugin: Spams the bot's inline button until a win is achieved."""
import asyncio
from telethon import events, functions
from telethon.tl.types import InputMediaDice
from selfbot.config import config

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}میویی$"))
    async def meowie_cheat(event: events.NewMessage.Event) -> None:
        # Find the bot's message with the button
        if not event.reply_to_msg_id:
            await event.edit("⚠️ لطفاً این دستور را در ریپلای به پیام ربات میویی بفرستید.")
            return
            
        bot_msg = await event.get_reply_message()
        if not bot_msg or not bot_msg.reply_markup:
            await event.edit("⚠️ پیام ربات دکمه شیشه‌ای ندارد.")
            return
            
        # Get the button's callback data
        button = bot_msg.reply_markup.rows[0].buttons[0]
        if not hasattr(button, 'data'):
            await event.edit("⚠️ دکمه شیشه‌ای معتبر نیست.")
            return
            
        data = button.data
        await event.edit("⏳ در حال تلاش برای برنده شدن...")
        
        # Spam the callback query
        for _ in range(50):
            try:
                # We need the bot's peer
                bot = await event.client.get_entity('@MeowieQVBot')
                res = await client(functions.messages.GetBotCallbackAnswerRequest(
                    peer=bot,
                    msg_id=bot_msg.id,
                    data=data
                ))
                # Wait for the bot to reply with the dice
                await asyncio.sleep(2)
                # Get the latest messages
                messages = await client.get_messages(event.chat_id, limit=5)
                for msg in messages:
                    if msg.from_id == bot.id and msg.media:
                        if isinstance(msg.media, InputMediaDice) and msg.media.value == 6:
                            await event.delete()
                            return
            except Exception as e:
                print(f"Meowie error: {e}")
                await asyncio.sleep(1)
                
        await event.edit("❌ متاسفانه موفق نشدیم.")
