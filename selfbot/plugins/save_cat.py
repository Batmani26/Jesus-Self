"""Save Cat plugin: Automatically clicks the rescue button on Meowie bot messages."""
import asyncio
from telethon import events
from selfbot.config import config

SAVE_CAT_STATUS = {"active": False, "scanning": False, "announce": False}
GLOBAL_SCAN_TASK = None
_CLICKED = set()
_INFLIGHT = set()
_RESCUE_KEYWORDS = (chr(1606)+chr(1580)+chr(1575)+chr(1578), chr(82)+chr(101)+chr(115)+chr(99)+chr(117)+chr(101))


def _has_rescue(msg):
    markup = getattr(msg, "reply_markup", None)
    if not markup:
        return False
    for row in markup.rows:
        for button in row.buttons:
            text = getattr(button, "text", "") or ""
            if any(k in text for k in _RESCUE_KEYWORDS):
                return True
    # Broader: if the message text looks like a Meowie cat notice and has any non-close button,
    # assume the rescue button is present (Meowie only shows it right after a cat appears).
    try:
        body = (getattr(msg, "text", "") or getattr(msg, "raw_text", "") or "")
        if ("پیشی" in body) or ("گربه" in body) or ("cat" in body.lower()) or ("Meow" in body):
            for row in markup.rows:
                for button in row.buttons:
                    t = (getattr(button, "text", "") or "").strip()
                    if t and "بستن" not in t and "close" not in t.lower() and "انصراف" not in t:
                        return True
    except Exception:
        pass
    return False


async def _try_rescue(client, chat_id, msg):
    key = (chat_id, msg.id)
    if key in _INFLIGHT or key in _CLICKED:
        return
    _INFLIGHT.add(key)
    try:
        for attempt in range(4):
            try:
                current = await client.get_messages(chat_id, ids=msg.id)
            except Exception as exc:
                print(f"[SAVE CAT] fetch error: {exc}")
                await asyncio.sleep(0.3)
                continue
            if not current or not getattr(current, "reply_markup", None):
                await asyncio.sleep(0.5)
                continue
            buttons = [b for row in current.reply_markup.rows for b in row.buttons]
            labels = [getattr(b, "text", "") or "" for b in buttons]
            print(f"[SAVE CAT] buttons available: {labels}")
            target = None
            # 1) keyword match
            for b in buttons:
                t = getattr(b, "text", "") or ""
                if any(k in t for k in _RESCUE_KEYWORDS):
                    target = b
                    break
            # 2) fallback: first visible non-close button
            if target is None:
                for b in buttons:
                    t = (getattr(b, "text", "") or "").strip()
                    if t and "بستن" not in t and "close" not in t.lower() and "انصراف" not in t:
                        target = b
                        break
            if target is None:
                print("[SAVE CAT] no usable button")
                break
            clicked_ok = False
            # Try button.click() first (it knows URL vs callback and correct msg)
            try:
                await target.click()
                clicked_ok = True
            except Exception as exc:
                print(f"[SAVE CAT] button.click() failed: {type(exc).__name__}: {exc}")
            # Fallback: raw callback answer
            if not clicked_ok:
                cb_data = getattr(target, "data", None)
                if cb_data:
                    try:
                        from telethon.tl.functions.messages import GetBotCallbackAnswerRequest
                        await client(GetBotCallbackAnswerRequest(peer=chat_id, msg_id=current.id, data=cb_data))
                        clicked_ok = True
                    except Exception as exc:
                        print(f"[SAVE CAT] callback answer failed: {type(exc).__name__}: {exc}")
            if clicked_ok:
                _CLICKED.add(key)
                print(f"[SAVE CAT] click OK on '{getattr(target, 'text', '?')}' in {chat_id} (try {attempt+1})")
                if SAVE_CAT_STATUS.get("announce"):
                    try:
                        await client.send_message("me", f"🐈 **پیشی نجات پیدا کرد!**\n\n📍 چت: <code>{chat_id}</code>")
                    except Exception as exc:
                        print(f"[SAVE CAT] announce error: {exc}")
                break
            await asyncio.sleep(0.3)
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
            await asyncio.sleep(20)
        except Exception as e:
            print(f"[SAVE CAT GLOBAL] Error: {e}")
            txt = str(e).lower()
            await asyncio.sleep(60 if "flood" in txt else 5)

def register(client) -> None:
    import re as _re
    _ep = _re.escape(config.PREFIX)
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{_ep}نجات پیشی\s*(روشن|خاموش)$"))
    async def toggle_save_cat(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        from bot.database import set_save_cat_active
        state = event.pattern_match.group(1)
        if state == "روشن":
            SAVE_CAT_STATUS["active"] = True
            await set_save_cat_active(me.id, 1)
            await event.edit("✅ **نجات پیشی روشن شد.** از این به بعد گربه‌ها رو نجات می‌دم!")
        else:
            SAVE_CAT_STATUS["active"] = False
            await set_save_cat_active(me.id, 0)
            await event.edit("❌ **نجات پیشی خاموش شد.**")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{_ep}اعلان نجات\s*(روشن|خاموش)$"))
    async def toggle_announce(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        from bot.database import set_save_cat_announce
        state = event.pattern_match.group(1)
        on = 1 if state == "روشن" else 0
        await set_save_cat_announce(me.id, on)
        SAVE_CAT_STATUS["announce"] = bool(on)
        if on:
            await event.edit("✅ **اعلام نجات روشن شد.** هر پیشی که نجات بدم توی Saved Messages اعلام می‌شه.")
        else:
            await event.edit("❌ **اعلام نجات خاموش شد.**")

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{_ep}نجات در تمامی چت ها$"))
    async def scan_all_chats(event: events.NewMessage.Event) -> None:
        global GLOBAL_SCAN_TASK
        me = await client.get_me()
        from bot.database import set_save_cat_scanning, set_save_cat_active
        SAVE_CAT_STATUS["scanning"] = True
        SAVE_CAT_STATUS["active"] = True
        await set_save_cat_scanning(me.id, 1)
        await set_save_cat_active(me.id, 1)
        await event.edit("⌛ **اسکنر سراسری روشن شد.** از این به بعد به صورت دائمی تمام گروه‌ها رو چک می‌کنم.")
        if GLOBAL_SCAN_TASK and not GLOBAL_SCAN_TASK.done():
            GLOBAL_SCAN_TASK.cancel()
        GLOBAL_SCAN_TASK = asyncio.create_task(global_scan_loop(client))

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{p}توقف نجات سراسری$"))
    async def stop_global_scan(event: events.NewMessage.Event) -> None:
        global GLOBAL_SCAN_TASK
        SAVE_CAT_STATUS["scanning"] = False
        try:
            me = await client.get_me()
            from bot.database import set_save_cat_scanning
            await set_save_cat_scanning(me.id, 0)
        except Exception:
            pass
        if GLOBAL_SCAN_TASK and not GLOBAL_SCAN_TASK.done():
            GLOBAL_SCAN_TASK.cancel()
        await event.edit("OK stopped global scan")

    async def _restore():
        try:
            me = await client.get_me()
            from bot.database import get_save_cat_active, get_save_cat_scanning
            SAVE_CAT_STATUS["active"] = await get_save_cat_active(me.id)
            from bot.database import get_save_cat_announce
            SAVE_CAT_STATUS["announce"] = await get_save_cat_announce(me.id)
            if await get_save_cat_scanning(me.id):
                SAVE_CAT_STATUS["scanning"] = True
                globals()["GLOBAL_SCAN_TASK"] = asyncio.create_task(global_scan_loop(client))
                print("[SAVE CAT] global scan restored from DB")
        except Exception as exc:
            print(f"[SAVE CAT] restore error: {exc}")
    asyncio.create_task(_restore())

    @client.on(events.NewMessage(incoming=True))
    async def on_cat_message(event: events.NewMessage.Event) -> None:
        if not (SAVE_CAT_STATUS.get("active") or SAVE_CAT_STATUS.get("scanning")):
            return
        try:
            if _has_rescue(event.message):
                print(f"[SAVE CAT] rescue detected in {event.chat_id} msg_id={event.message.id}")
                await _try_rescue(client, event.chat_id, event.message)
        except Exception as exc:
            print(f"[SAVE CAT] handler error: {exc}")
