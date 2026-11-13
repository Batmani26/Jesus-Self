"""Bowling plugin: `.بولینگ` throws a bowling ball until it gets a strike."""
import asyncio
from telethon import events
from telethon.tl.types import InputMediaDice
from selfbot.config import config

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}بولینگ$"))
    async def bowling_cmd(event: events.NewMessage.Event) -> None:
        await event.delete()
        
        # We will try up to 100 times to get a strike (value 6)
        for _ in range(200):
            msg = await client.send_message(event.chat_id, file=InputMediaDice("🎳"))
            
            if msg and msg.media and hasattr(msg.media, 'value'):
                if msg.media.value == 6:
                    return
            
            asyncio.create_task(msg.delete())
