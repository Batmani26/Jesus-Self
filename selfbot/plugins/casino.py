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
        
        # We will try up to 500 times sequentially with maximum network speed
        for _ in range(500):
            try:
                msg = await client.send_message(event.chat_id, file=InputMediaDice("🎰"))
                
                if msg and msg.media and hasattr(msg.media, 'value'):
                    val = msg.media.value
                    if isinstance(val, int) and val >= 43:
                        # High score! Keep it.
                        return
                
                asyncio.create_task(msg.delete())
            except Exception as e:
                print(f"Casino error: {e}")
                await asyncio.sleep(0.1)
