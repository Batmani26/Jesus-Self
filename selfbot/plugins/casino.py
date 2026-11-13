"""Casino plugin: `.کازینو` spins the slot until it hits the jackpot."""
import asyncio
from telethon import events
from telethon.tl.types import InputMediaDice
from selfbot.config import config

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}کازینو$"))
    async def casino_cmd(event: events.NewMessage.Event) -> None:
        await event.delete()
        
        # We will try up to 500 times to hit the jackpot (value 64)
        for _ in range(500):
            msg = await client.send_message(event.chat_id, file=InputMediaDice("🎰"))
            
            if msg and msg.media and hasattr(msg.media, 'value'):
                if msg.media.value == 64:
                    # Jackpot! Keep it.
                    return
            
            asyncio.create_task(msg.delete())
