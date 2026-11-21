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
    """Find the button matching the user's mode. Fallback: first usable (non-close, non-empty) button."""
    if not markup:
        return None
    kws = MODE_KEYWORDS.get(mode, MODE_KEYWORDS["sell"])
    # 1) Exact keyword match by visible text
    for row in markup.rows:
        for b in row.buttons:
            lbl = getattr(b, "text", "") or ""
            for kw in kws:
                if kw in lbl:
                    return b
    # 2) Fallback: first button that has a real label (not zero-width only)
    def _real(lbl: str) -> bool:
        return bool(lbl) and lbl.strip("\u200b\u200c\u200d\ufeff \t\n").strip() != ""
    for row in markup.rows:
        for b in row.buttons:
            lbl = getattr(b, "text", "") or ""
            if _real(lbl) and "بستن" not in lbl and "close" not in lbl.lower() and "انصراف" not in lbl:
                return b
    # 3) Last resort: first button by INDEX (mode order: sell=0, cat=1, fridge=2)
    idx = {"sell": 0, "cat": 1, "fridge": 2}.get(mode, 0)
    flat = [b for row in markup.rows for b in row.buttons]
    if 0 <= idx < len(flat):
        return flat[idx]
    return flat[0] if flat else None


async def _click_button(client, peer, msg_id, button):
    """Click robustly. Try button.click() first (handles peer resolution), then raw callback."""
    # اول button.click() را امتحان کن — خودش peer را حل می‌کند
    try:
        await button.click()
        return True
    except Exception as e:
        print(f"[FISH] button.click() failed: {type(e).__name__}: {e}")
    # اگر شکست خورد، raw callback را امتحان کن
    data = getattr(button, "data", None)
    if data:
        try:
            from telethon.tl.functions.messages import GetBotCallbackAnswerRequest
            await client(GetBotCallbackAnswerRequest(peer=peer, msg_id=msg_id, data=data))
            return True
        except Exception as e:
            print(f"[FISH] callback request failed: {type(e).__name__}: {e}")
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
    # Fire 3 rapid attempts (button data may repeat but extra calls are ignored after first success)
    ok = False
    for attempt in range(3):
        try:
            if await _click_button(client, chat_id, msg.id, btn):
                ok = True
                print(f"[FISH] click {attempt+1}/3 OK on '{getattr(btn, 'text', '?')}' for {rarity}/{mode}")
        except Exception:
            pass
        if attempt < 2:
            await asyncio.sleep(0.05)
    return ok
