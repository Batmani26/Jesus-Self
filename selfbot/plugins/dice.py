"""Dice plugin: `.تاس <1-6>` throws a dice until it lands on the desired number."""
import asyncio
from telethon import events
from telethon.tl.types import InputMediaDice
from selfbot.config import config

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}تاس ([1-6])$"))
    async def dice_cmd(event: events.NewMessage.Event) -> None:
        desired = int(event.pattern_match.group(1))
        await event.delete()
        
        # We will try up to 20 times to get the desired number
        for _ in range(20):
            msg = await client.send_message(event.chat_id, file=InputMediaDice("🎲"))
            await asyncio.sleep(2.5) # Wait for the dice animation to finish
            
            # We need to fetch the message again to get the result
            msg = await client.get_messages(event.chat_id, ids=msg.id)
            if msg and msg.media and hasattr(msg.media, 'value'):
                if msg.media.value == desired:
                    # Found the desired number! Keep it.
                    return
            
            # Not the desired number, delete and try again
            await msg.delete()
            await asyncio.sleep(0.1) # Small delay before throwing again

        # If we exit the loop without success, send a fallback message
        await client.send_message(event.chat_id, f"❌ متاسفانه بعد از ۲۰ بار تاس انداختن، عدد {desired} نیامد!")
