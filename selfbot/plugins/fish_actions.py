"""Fishing action helper: detect caught fish rarity and click the matching action button."""
import asyncio

RARITY_MARKERS = (
    ("legendary", ("افسانه‌ای", "افسانه ای", "افسانه‌ ئی")),
    ("epic", ("حماسی",)),
    ("rare", ("کمیاب",)),
    ("common", ("معمولی", "عادی")),
)

MODE_KEYWORDS = {
    "sell": ("فروش", "بفروش"),
    "cat": ("پیشی", "گربه", "بخور"),
    "fridge": ("یخچال", "ذخیره"),
}


def detect_rarity(text: str):
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


async def handle_catch(client, chat_id, sent_msg_id, modes, timeout=25):
    """Poll the bot reply and click the action button for the caught rarity."""
    waited = 0
    while waited < timeout:
        await asyncio.sleep(1.5)
        waited += 1.5
        try:
            reply = await client.get_messages(chat_id, ids=sent_msg_id)
        except Exception:
            continue
        if not reply:
            continue
        target = reply
        if getattr(reply, "reply_to_msg_id", None):
            try:
                target = await reply.get_reply_message() or reply
            except Exception:
                target = reply
        text = getattr(target, "text", "") or ""
        if "ماهی فرار کرد" in text:
            return {"rarity": None, "mode": None, "action": "escaped"}
        rarity = detect_rarity(text)
        if not rarity:
            continue
        mode = (modes or {}).get(rarity, "sell")
        button = _find_button(getattr(target, "reply_markup", None), MODE_KEYWORDS.get(mode, ()))
        if button:
            try:
                await button.click()
            except Exception as exc:
                print(f"[FISH] click error: {exc}")
        return {"rarity": rarity, "mode": mode, "action": "clicked" if button else "no_button"}
    return {"rarity": None, "mode": None, "action": "timeout"}
