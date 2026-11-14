"""Save Cat plugin: Automatically clicks the rescue button on Meowie bot messages."""
import asyncio
from telethon import events
from selfbot.config import config

def register(client) -> None:
    p = config.PREFIX
    active = False

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}نجات پیشی (روشن|خاموش)$"))
    async def toggle_save_cat(event: events.NewMessage.Event) -> None:
        nonlocal active
        state = event.pattern_match.group(1)
        if state == "روشن":
            active = True
            await event.edit("✅ **نجات پیشی روشن شد.** از این به بعد گربه‌ها رو نجات می‌دم!")
        else:
            active = False
            await event.edit("❌ **نجات پیشی خاموش شد.**")

    @client.on(events.NewMessage(incoming=True))
    async def on_cat_message(event: events.NewMessage.Event) -> None:
        if not active:
            return
            
        # Check if the message is from Meowie bot and contains the rescue text
        if event.sender_id and event.message.reply_markup:
            text = event.text or ""
            if "🐈 یه پیشی خیابونی" in text or "نجات پیشی خیابونی" in text:
                # Find the button with 'نجات'
                for row in event.message.reply_markup.rows:
                    for button in row.buttons:
                        if "نجات" in button.text:
                            try:
                                await button.click()
                                print(f"[SAVE CAT] Clicked rescue button in chat {event.chat_id}")
                            except Exception as e:
                                print(f"[SAVE CAT ERROR] {e}")
                            return
