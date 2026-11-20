"""Fishing plugin: Automatically sends 'ماهی' in the target chat."""
import asyncio
import re
from telethon import events
from selfbot.config import config

FISHING_TASKS = {}

async def fishing_loop_wrapper(client, chat_id, interval_str, user_id=None, immediate=False):
    if not interval_str:
        return
    try:
        parts = interval_str.strip().split(':')
        # Format is MINUTES:SECONDS (first = minutes, second = seconds)
        cooldown = (int(parts[0]) * 60) + int(parts[1])
        if cooldown <= 0:
            raise ValueError()
    except Exception:
        return
    loop = asyncio.get_event_loop()
    # First send: immediate (right after .ماهیگیری روشن) or wait full cooldown
    next_send = loop.time() if immediate else loop.time() + cooldown
    while True:
        try:
            if user_id is None:
                me = await client.get_me()
                owner_id = me.id
            else:
                owner_id = user_id
            delay = next_send - loop.time()
            if delay > 0:
                await asyncio.sleep(delay)
            while not client.is_connected():
                await asyncio.sleep(2)
            try:
                await client.send_message(chat_id, "ماهی")
                print(f"[FISH] sent ماهی to {chat_id}")
            except Exception as exc:
                print(f"[FISH] send error: {exc}")
            # Clicking is handled instantly by the incoming-message event handler
            next_send += cooldown
            if next_send < loop.time():
                next_send = loop.time() + cooldown
        except asyncio.CancelledError:
            break
        except Exception as exc:
            print(f"[FISH ERROR] {exc}")
            await asyncio.sleep(3)

def register(client) -> None:
    p = config.PREFIX

    # EVENT-DRIVEN click: fires the moment Meowie posts a catch message (has rarity + buttons).
    _me_cache = {"id": None}
    async def _own():
        if _me_cache["id"] is None:
            try:
                me = await client.get_me()
                _me_cache["id"] = me.id
            except Exception:
                pass
        return _me_cache["id"]

    @client.on(events.NewMessage(incoming=True))
    async def on_meowie_catch(event: events.NewMessage.Event) -> None:
        try:
            text = event.raw_text or ""
            if not text:
                return
            # Quick checks — fire only when Meowie posts a CATCH (not escape)
            if "فرار" in text:
                return
            if "گرفتی" not in text and "سطح" not in text:
                return
            markup = getattr(event.message, "reply_markup", None)
            if not markup:
                return
            from selfbot.plugins.fish_actions import try_click_now
            uid = await _own()
            # Fire 2 parallel click attempts (race — first wins)
            await try_click_now(client, event.chat_id, event.message, owner_id=uid)
        except Exception as exc:
            print(f"[FISH] on_meowie_catch error: {exc}")

    @client.on(events.NewMessage(outgoing=True, pattern="^" + re.escape(p) + "تنظیم زمان ماهیگیری (\\d+:\\d+)$"))
    async def set_fishing_time(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        interval = event.pattern_match.group(1).strip()
        from bot.database import set_fishing_interval
        parts = interval.strip().split(':')
        mins = int(parts[0]); secs = int(parts[1])
        total = mins * 60 + secs
        await set_fishing_interval(me.id, interval)
        await event.edit(f"✅ زمان ماهیگیری شما روی **{interval}** (دقیقه:ثانیه) = هر **{total}** ثانیه تنظیم شد.")

    @client.on(events.NewMessage(outgoing=True, pattern="^" + re.escape(p) + "ماهیگیری روشن$"))
    async def start_fishing(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        from bot.database import get_meow_target_db, get_fishing_interval, set_fishing_active
        
        target = await get_meow_target_db(me.id)
        interval = await get_fishing_interval(me.id)
        if not target or not target.get('chat_id'):
            await event.edit("⚠️ **خطا:** لطفاً ابتدا چت مقصد را با دستور `.تنظیم میویی` مشخص کنید.")
            return
        if not interval:
            await event.edit("⚠️ **خطا:** لطفاً ابتدا زمان ماهیگیری خود را با دستور `.تنظیم زمان ماهیگیری 4:20` (دقیقه:ثانیه) تنظیم کنید.")
            return
            
        chat_id = int(target['chat_id'])
        for cid in list(FISHING_TASKS.keys()):
            FISHING_TASKS[cid].cancel()
            del FISHING_TASKS[cid]
        if chat_id in FISHING_TASKS:
            await event.edit("⚠️ ماهیگیری در این چت از قبل روشن است.")
            return
            
        await event.edit(f"✅ شروع ماهیگیری در چت **{target['chat_title']}** با تایم **{interval}**...")
        FISHING_TASKS[chat_id] = asyncio.create_task(fishing_loop_wrapper(client, chat_id, interval, me.id, immediate=True))
        await set_fishing_active(me.id, 1)

    @client.on(events.NewMessage(outgoing=True, pattern="^" + re.escape(p) + "ماهیگیری خاموش$"))
    async def stop_fishing(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        from bot.database import set_fishing_active, get_meow_target_db
        _t = await get_meow_target_db(me.id)
        chat_id = int(_t[chr(39)+chr(99)+chr(104)+chr(97)+chr(116)+chr(95)+chr(105)+chr(100)+chr(39)]) if _t and _t.get(chr(39)+chr(99)+chr(104)+chr(97)+chr(116)+chr(95)+chr(105)+chr(100)+chr(39)) else event.chat_id
        if chat_id in FISHING_TASKS:
            FISHING_TASKS[chat_id].cancel()
            del FISHING_TASKS[chat_id]
            await set_fishing_active(me.id, 0)
            await event.edit("❌ ماهیگیری در این چت متوقف شد.")
        else:
            await set_fishing_active(me.id, 0)
            await event.edit("⚠️ ماهیگیری در این چت روشن نیست.")
