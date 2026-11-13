"""Farm plugin: `.فارم تاس <1-6>` rolls dice until the desired number and sends it."""
import asyncio
from telethon import events
from telethon.tl.types import InputMediaDice
from selfbot.config import config

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}فارم تاس ([1-6])$"))
    async def farm_dice(event: events.NewMessage.Event) -> None:
        desired = int(event.pattern_match.group(1))
        
        # Check if the command is a reply to a message
        if not event.reply_to_msg_id:
            await event.edit("⚠️ لطفاً این دستور را **در ریپلای** به پیام ربات میویی بفرستید.")
            return
            
        bot_msg_id = event.reply_to_msg_id
        chat_id = event.chat_id
        
        await event.edit(f"⏳ در حال فارم کردن تاس {desired}...")
        
        for _ in range(300):
            msg = await client.send_message("me", file=InputMediaDice("🎲"))
            if msg and msg.media and hasattr(msg.media, 'value'):
                if msg.media.value == desired:
                    # Found it! Forward it as a reply to the bot's message in the group
                    await client.forward_messages(chat_id, msg.id, from_peer="me", reply_to=bot_msg_id)
                    await event.delete()
                    return
            asyncio.create_task(msg.delete())
            
        await event.edit("❌ متاسفانه تاس مورد نظر پیدا نشد. لطفاً دوباره تلاش کنید.")
