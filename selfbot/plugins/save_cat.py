"""Save Cat plugin: Automatically clicks the rescue button on Meowie bot messages."""
import asyncio
from telethon import events
from selfbot.config import config

SAVE_CAT_STATUS = {"active": False, "scanning": False}
GLOBAL_SCAN_TASK = None
_CLICKED = set()
_INFLIGHT = set()
_RESCUE_KEYWORDS = (chr(1606)+chr(1580)+chr(1575)+chr(1578), chr(82)+chr(101)+chr(115)+chr(99)+chr(117)+chr(101))


def _has_rescue(msg):
    markup = getattr(msg, chr(114)+chr(101)+chr(112)+chr(108)+chr(121)+chr(95)+chr(109)+chr(97)+chr(114)+chr(107)+chr(117)+chr(112), None)
    if not markup:
        return False
    for row in markup.rows:
        for button in row.buttons:
            text = getattr(button, chr(116)+chr(101)+chr(120)+chr(116), chr(39)+chr(39)) or chr(39)+chr(39)
            if any(k in text for k in _RESCUE_KEYWORDS):
                return True
    return False


async def _try_rescue(client, chat_id, msg):
    key = (chat_id, msg.id)
    if key in _INFLIGHT or key in _CLICKED:
        return
    _INFLIGHT.add(key)
    try:
        for _ in range(15):
            current = await client.get_messages(chat_id, ids=msg.id)
            if not current or not _has_rescue(current):
                break
            clicked_any = False
            for row in current.reply_markup.rows:
                for button in row.buttons:
                    text = getattr(button, chr(116)+chr(101)+chr(120)+chr(116), chr(39)+chr(39)) or chr(39)+chr(39)
                    if not any(k in text for k in _RESCUE_KEYWORDS):
                        continue
                    try:
                        await button.click()
                        clicked_any = True
                        await asyncio.sleep(0.15)
                    except Exception:
                        pass
            if not clicked_any:
                break
            await asyncio.sleep(0.25)
        _CLICKED.add(key)
    finally:
        _INFLIGHT.discard(key)


async def global_scan_loop(client):
    while SAVE_CAT_STATUS["scanning"]:
        try:
            async for dialog in client.iter_dialogs():
                if not SAVE_CAT_STATUS["scanning"]:
                    break
                if dialog.is_group:
                    try:
                        messages = await client.get_messages(dialog.id, limit=15)
                        for msg in messages or []:
                            if _has_rescue(msg):
                                await _try_rescue(client, dialog.id, msg)
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
        SAVE_CAT_STATUS["active"] = True
        await event.edit("⏳ **اسکنر سراسری روشن شد.** از این به بعد به صورت دائمی تمام گروه‌ها رو چک می‌کنم.")
        
        if GLOBAL_SCAN_TASK and not GLOBAL_SCAN_TASK.done():
            GLOBAL_SCAN_TASK.cancel()
            
        GLOBAL_SCAN_TASK = asyncio.create_task(global_scan_loop(client))

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{p}توقف نجات سراسری$"))
    async def stop_global_scan(event: events.NewMessage.Event) -> None:
        global GLOBAL_SCAN_TASK
        SAVE_CAT_STATUS["scanning"] = False
        if GLOBAL_SCAN_TASK and not GLOBAL_SCAN_TASK.done():
            GLOBAL_SCAN_TASK.cancel()
        await event.edit("OK stopped global scan")

    @client.on(events.NewMessage(incoming=True))
    async def on_cat_message(event: events.NewMessage.Event) -> None:
        if not (SAVE_CAT_STATUS[chr(97)+chr(99)+chr(116)+chr(105)+chr(118)+chr(101)] or SAVE_CAT_STATUS[chr(115)+chr(99)+chr(97)+chr(110)+chr(110)+chr(105)+chr(110)+chr(103)]):
            return
        if _has_rescue(event.message):
            await _try_rescue(client, event.chat_id, event.message)
