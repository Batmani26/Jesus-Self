"""Save Cat plugin: Automatically clicks the rescue button on Meowie bot messages."""
import asyncio
from telethon import events
from selfbot.config import config

SAVE_CAT_STATUS = {"active": False, "scanning": False}

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}نجات پیشی (روشن|خاموش)$"))
    async def toggle_save_cat(event: events.NewMessage.Event) -> None:
        state = event.pattern_match.group(1)
        if state == "روشن":
            SAVE_CAT_STATUS["active"] = True
            await event.edit("✅ **نجات پیشی روشن شد.** از این به بعد گربه‌ها رو نجات می‌دم!")
        else:
            SAVE_CAT_STATUS["active"] = False
            await event.edit("❌ **نجات پیشی خاموش شد.**")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}نجات در تمامی چت ها$"))
    async def scan_all_chats(event: events.NewMessage.Event) -> None:
        SAVE_CAT_STATUS["scanning"] = True
        await event.edit("⏳ در حال جستجو در تمام گروه‌ها برای نجات گربه‌ها...")
        count = 0
        
        async for dialog in client.iter_dialogs():
            if dialog.is_group:
                try:
                    # Check last 5 messages in each group
                    messages = await client.get_messages(dialog.id, limit=5)
                    for msg in messages:
                        if msg.reply_markup:
                            for row in msg.reply_markup.rows:
                                for button in row.buttons:
                                    if "نجات" in button.text:
                                        try:
                                            await button.click()
                                            count += 1
                                            await asyncio.sleep(0.5) # Small delay to avoid flood
                                        except Exception:
                                            pass
                except Exception as e:
                    print(f"[SAVE CAT] Error in {dialog.name}: {e}")
                    
        SAVE_CAT_STATUS["scanning"] = False
        await event.edit(f"✅ **جستجو تمام شد.** تعداد {count} گربه نجات پیدا کرد.")

    @client.on(events.NewMessage(incoming=True))
    async def on_cat_message(event: events.NewMessage.Event) -> None:
        if not SAVE_CAT_STATUS["active"]:
            return
            
        if event.message.reply_markup:
            for row in event.message.reply_markup.rows:
                for button in row.buttons:
                    if "نجات" in button.text:
                        # Keep clicking until the button disappears or changes
                        for _ in range(10):
                            try:
                                await button.click()
                                print(f"[SAVE CAT] Clicked rescue button in chat {event.chat_id}")
                                await asyncio.sleep(0.5)
                                # Check if the button still exists
                                updated_msg = await event.client.get_messages(event.chat_id, ids=event.message.id)
                                if not updated_msg or not updated_msg.reply_markup:
                                    break
                            except Exception as e:
                                print(f"[SAVE CAT ERROR] {e}")
                                break
                        return
