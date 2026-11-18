"""Fishing action helper: detect caught fish rarity and click the matching action button."""
import asyncio

RARITY_MARKERS = (
    ("legendary", ("افسانه‌ای", "افسانه ای", "افسانه‌ ئی", "افسانه")),
    ("epic", ("حماسی",)),
    ("rare", ("کمیاب", "کمیاب‌")),
    ("common", ("معمولی", "عادی")),
)

MODE_KEYWORDS = {
    "sell": ("فروش", "بفروش"),
    "cat": ("پیشی", "گربه", "بخور"),
    "fridge": ("یخچال", "ذخیره", "بنداز"),
}


def detect_rarity(text):
    if not text:
        return None
    for rarity, markers in RARITY_MARKERS:
        for marker in markers:
            if marker in text:
                return rarity
    return None


def _find_button(markup, keywords):
    if not markup:
        return None
    for row in markup.rows:
        for button in row.buttons:
            label = getattr(button, "text", "") or ""
            for kw in keywords:
                if kw in label:
                    return button
    return None


def _all_buttons(markup):
    out = []
    if not markup:
        return out
    for row in markup.rows:
        for button in row.buttons:
            out.append(getattr(button, "text", "") or "")
    return out


async def _find_bot_reply(client, chat_id, sent_msg_id):
    """Find the message that replies to our 'ماهی' message."""
    try:
        messages = await client.get_messages(chat_id, limit=8)
    except Exception as exc:
        print(f"[FISH] fetch error: {exc}")
        return None
    for m in messages or []:
        if getattr(m, "reply_to_msg_id", None) == sent_msg_id:
            return m
    # Fallback: any recent bot message that has a rarity marker AND a reply_markup with buttons
    for m in messages or []:
        txt = getattr(m, "text", "") or ""
        markup = getattr(m, "reply_markup", None)
        if markup and detect_rarity(txt):
            return m
    for m in messages or []:
        txt = getattr(m, "text", "") or ""
        if ("سطح" in txt) and (("ماهی" in txt) or ("گرفتی" in txt)):
            return m
    return None


async def handle_catch(client, chat_id, sent_msg_id, modes, timeout=40):
    waited = 0.0
    while waited < timeout:
        await asyncio.sleep(0.7)
        waited += 0.7

        bot_msg = await _find_bot_reply(client, chat_id, sent_msg_id)
        if not bot_msg:
            continue

        text = getattr(bot_msg, "text", "") or ""
        rarity = detect_rarity(text)
        markup = getattr(bot_msg, "reply_markup", None)

        # If the message still has action buttons, act FAST — even if a later line says 'فرار کرد'
        # (meowie appends 'فرار کرد' only AFTER timeout, but if we click quickly we win)
        if rarity and markup:
            pass  # proceed to click immediately
        elif "فرار کرد" in text and not markup:
            print(f"[FISH] escaped: {text.splitlines()[0] if text else ''}")
            return {"rarity": None, "mode": None, "action": "escaped"}
        elif not rarity:
            continue

        mode = (modes or {}).get(rarity, "sell")
        keywords = MODE_KEYWORDS.get(mode, MODE_KEYWORDS["sell"])

        clicked = False
        print(f"[FISH] buttons available: {_all_buttons(getattr(bot_msg, 'reply_markup', None))}")
        for attempt in range(3):
            button = _find_button(getattr(bot_msg, "reply_markup", None), keywords)
            if not button:
                # fallback: try any button whose label is not 'بستن' / 'close'
                mk = getattr(bot_msg, "reply_markup", None)
                if mk:
                    for row in mk.rows:
                        for b in row.buttons:
                            lbl = getattr(b, "text", "") or ""
                            if lbl and "بستن" not in lbl and "close" not in lbl.lower():
                                button = b
                                break
                        if button:
                            break
            if not button:
                break
            try:
                await button.click()
                clicked = True
                print(f"[FISH] {rarity}/{mode} clicked (try {attempt + 1})")
            except Exception as exc:
                print(f"[FISH] click error: {exc}")
            await asyncio.sleep(0.25)
            try:
                bot_msg = await client.get_messages(chat_id, ids=bot_msg.id)
                if not bot_msg or not getattr(bot_msg, "reply_markup", None):
                    break
            except Exception:
                break

        return {"rarity": rarity, "mode": mode, "action": "clicked" if clicked else "no_button"}

    return {"rarity": None, "mode": None, "action": "timeout"}
