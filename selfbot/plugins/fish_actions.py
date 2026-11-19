"""Fishing action helper: event-driven click on the Meowie bot reply.

We register a global NewMessage(incoming=True) handler once; when the bot
posts a catch message with rarity + inline buttons, we click immediately
(via raw GetBotCallbackAnswerRequest) BEFORE the fish escapes.
"""
import asyncio

RARITY_MARKERS = (
    ("legendary", ("افسانه‌ای", "افسانه ای", "افسانه", "اسطوره‌ای", "اسطوره ای")),
    ("epic", ("حماسی",)),
    ("rare", ("کمیاب", "کمیاب‌")),
    ("common", ("معمولی", "عادی")),
)

MODE_KEYWORDS = {
    "sell": ("فروش ماهی", "فروش", "بفروش"),
    "cat": ("بده پیشی بخوره", "پیشی بخوره", "پیشی", "گربه", "بخور"),
    "fridge": ("بندازش تو یخچال", "یخچال", "ذخیره", "بنداز"),
}


def detect_rarity(text):
    if not text:
        return None
    for rarity, markers in RARITY_MARKERS:
        for marker in markers:
            if marker in text:
                return rarity
    return None


def _all_buttons(markup):
    out = []
    if not markup:
        return out
    for row in markup.rows:
        for button in row.buttons:
            out.append(getattr(button, "text", "") or "")
    return out


def _pick_button(markup, mode):
    """Find the button matching the user's mode. Fallback: any non-close button."""
    if not markup:
        return None
    kws = MODE_KEYWORDS.get(mode, MODE_KEYWORDS["sell"])
    # 1) Exact keyword match
    for row in markup.rows:
        for b in row.buttons:
            lbl = getattr(b, "text", "") or ""
            for kw in kws:
                if kw in lbl:
                    return b
    # 2) Fallback: any button whose label is not 'بستن' / 'close' / 'انصراف'
    for row in markup.rows:
        for b in row.buttons:
            lbl = getattr(b, "text", "") or ""
            if lbl and "بستن" not in lbl and "close" not in lbl.lower() and "انصراف" not in lbl:
                return b
    return None


async def _click_button(client, peer, msg_id, button):
    """Use raw GetBotCallbackAnswerRequest for maximum compatibility with selfbots."""
    data = getattr(button, "data", None)
    if data is None:
        try:
            await button.click()
            return True
        except Exception as e:
            print(f"[FISH] fallback click failed: {e}")
            return False
    try:
        from telethon.tl.functions.messages import GetBotCallbackAnswerRequest
        await client(GetBotCallbackAnswerRequest(peer=peer, msg_id=msg_id, data=data))
        return True
    except Exception as e:
        print(f"[FISH] GetBotCallbackAnswer failed: {type(e).__name__}: {e}")
        return False


async def handle_catch(client, chat_id, sent_msg_id, modes, timeout=40):
    """Kept for compatibility — the event-driven handler does the real work.
    This simply returns after a short wait so callers don't hang."""
    await asyncio.sleep(2)
    return {"rarity": None, "mode": None, "action": "event-driven"}


async def try_click_now(client, chat_id, msg, owner_id=None):
    """Click the correct mode button on a catch message RIGHT NOW. Returns True if clicked."""
    text = getattr(msg, "text", "") or ""
    markup = getattr(msg, "reply_markup", None)
    rarity = detect_rarity(text)
    if not rarity or not markup:
        return False
    # Load per-user fish modes
    modes = {}
    try:
        from bot.database import get_fish_modes
        if owner_id is None:
            me = await client.get_me()
            owner_id = me.id
        modes = await get_fish_modes(owner_id)
    except Exception:
        pass
    mode = (modes or {}).get(rarity, "sell")
    print(f"[FISH] catch detected rarity={rarity} mode={mode} buttons={_all_buttons(markup)}")
    btn = _pick_button(markup, mode)
    if not btn:
        print("[FISH] no button matched!")
        return False
    ok = await _click_button(client, chat_id, msg.id, btn)
    print(f"[FISH] click {'OK' if ok else 'FAILED'} on '{getattr(btn, 'text', '?')}' for {rarity}/{mode}")
    return ok
