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
        
        # We will try up to 10 batches of 50 concurrent rolls to hit the jackpot (value 64)
        for _ in range(10):
            tasks = []
            for _ in range(50):
                tasks.append(client.send_message(event.chat_id, file=InputMediaDice("🎰")))
            
            messages = await asyncio.gather(*tasks)
            
            for msg in messages:
                if msg and msg.media and hasattr(msg.media, 'value') and msg.media.value == 64:
                    # Jackpot! Delete all other messages in this batch and keep the winner
                    for m in messages:
                        if m.id != msg.id:
                            asyncio.create_task(m.delete())
                    return
            
            # No jackpot in this batch, delete all
            for msg in messages:
                asyncio.create_task(msg.delete())
