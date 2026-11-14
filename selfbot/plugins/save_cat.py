"""Save Cat plugin: Automatically clicks the rescue button on Meowie bot messages."""
import asyncio
from telethon import events
from selfbot.config import config

SAVE_CAT_STATUS = {"active": False, "scanning": False}
GLOBAL_SCAN_TASK = None

async def global_scan_loop(client):
    while SAVE_CAT_STATUS["scanning"]:
        try:
            async for dialog in client.iter_dialogs():
                if not SAVE_CAT_STATUS["scanning"]:
                    break
                if dialog.is_group:
                    try:
                        messages = await client.get_messages(dialog.id, limit=3)
                        for msg in messages:
                            if msg.reply_markup:
                                for row in msg.reply_markup.rows:
                                    for button in row.buttons:
                                        if "نجات" in button.text:
                                            try:
                                                await button.click()
                                                await asyncio.sleep(0.2)
                                            except Exception:
                                                pass
                    except Exception:
                        pass
            await asyncio.sleep(1) # Wait before next full scan
        except Exception as e:
            print(f"[SAVE CAT GLOBAL] Error: {e}")
            await asyncio.sleep(5)

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}نجات پیشی\s*(روشن|خاموش)$"))
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
        global GLOBAL_SCAN_TASK
        SAVE_CAT_STATUS["scanning"] = True
        await event.edit("⏳ **اسکنر سراسری روشن شد.** از این به بعد به صورت دائمی تمام گروه‌ها رو چک می‌کنم.")
        
        if GLOBAL_SCAN_TASK and not GLOBAL_SCAN_TASK.done():
            GLOBAL_SCAN_TASK.cancel()
            
        GLOBAL_SCAN_TASK = asyncio.create_task(global_scan_loop(client))

    @client.on(events.NewMessage(incoming=True))
    async def on_cat_message(event: events.NewMessage.Event) -> None:
        if not SAVE_CAT_STATUS["active"]:
            return
            
        if event.message.reply_markup:
            for row in event.message.reply_markup.rows:
                for button in row.buttons:
                    if "نجات" in button.text:
                        for _ in range(10):
                            try:
                                await button.click()
                                print(f"[SAVE CAT] Clicked rescue button in chat {event.chat_id}")
                                await asyncio.sleep(0.5)
                                updated_msg = await client.get_messages(event.chat_id, ids=event.message.id)
                                if not updated_msg or not updated_msg.reply_markup:
                                    break
                            except Exception as e:
                                print(f"[SAVE CAT ERROR] {e}")
                                break
                        return
