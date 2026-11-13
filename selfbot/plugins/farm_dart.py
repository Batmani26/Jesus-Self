"""Farm plugin for dart: `.فارم دارت` rolls dart until bullseye and forwards as reply."""
import asyncio
from telethon import events
from telethon.tl.types import InputMediaDice
from selfbot.config import config

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}فارم دارت$"))
    async def farm_dart(event: events.NewMessage.Event) -> None:
        if not event.reply_to_msg_id:
            await event.edit("⚠️ لطفاً این دستور را **در ریپلای** به پیام ربات میویی بفرستید.")
            return
            
        bot_msg_id = event.reply_to_msg_id
        chat_id = event.chat_id
        
        await event.edit("⏳ در حال فارم کردن دارت (هدف‌گیری وسط)...")
        
        for _ in range(300):
            msg = await client.send_message("me", file=InputMediaDice("🎯"))
            if msg and msg.media and hasattr(msg.media, 'value'):
                if msg.media.value == 6:
                    await client.forward_messages(chat_id, msg.id, from_peer="me", reply_to=bot_msg_id)
                    await event.delete()
                    return
            asyncio.create_task(msg.delete())
            
        await event.edit("❌ متاسفانه دارت به هدف نخورد. لطفاً دوباره تلاش کنید.")
