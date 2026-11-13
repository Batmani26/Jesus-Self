"""Dart plugin: `.دارت` throws a dart until it hits the bullseye."""
import asyncio
from telethon import events
from telethon.tl.types import InputMediaDice
from selfbot.config import config

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}دارت$"))
    async def dart_cmd(event: events.NewMessage.Event) -> None:
        await event.delete()
        
        # We will try up to 100 times to hit the bullseye (value 6)
        for _ in range(100):
            msg = await client.send_message(event.chat_id, file=InputMediaDice("🎯"))
            
            # The value is available immediately in the API response
            if msg and msg.media and hasattr(msg.media, 'value'):
                if msg.media.value == 6:
                    # Bullseye! Keep it.
                    return
            
            # Fire and forget the delete to maximize speed
            asyncio.create_task(msg.delete())
