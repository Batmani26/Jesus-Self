"""Fishing panel builder: rarity rows with cyclable action modes."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

RARITY_LABELS = {
    "legendary": ("🌟", "افسانه‌ای"),
    "epic": ("🔥", "حماسی"),
    "rare": ("💎", "کمیاب"),
    "common": ("🍃", "معمولی"),
}
MODE_LABELS = {
    "sell": ("💰", "فروش"),
    "cat": ("🐱", "دادن به پیشی"),
    "fridge": ("🧊", "یخچال"),
}

def build_fishing_text(target_text: str, status_text: str, interval_display: str, modes: dict) -> str:
    lines = [
        "🎣 <b>ماهیگیری خودکار</b>",
        "",
        target_text,
        f"📊 وضعیت: {status_text}",
        f"⏱ تایم تنظیم شده: <b>{interval_display}</b>",
        "",
        "<b>⚙️ کار خودکار روی هر سطح:</b>",
    ]
    for rarity, (emoji, name) in RARITY_LABELS.items():
        mode = modes.get(rarity, "sell")
        memoji, mname = MODE_LABELS[mode]
        lines.append(f"{emoji} <b>{name}</b> → {memoji} {mname}")
    lines += [
        "",
        "<blockquote>هر بار روی دکمهٔ یک سطح بزنی، کار خودکار آن سطح بین «فروش»، «دادن به پیشی» و «یخچال» می‌چرخد.</blockquote>",
        "",
        "<b>دستورات:</b>",
        "<code>.تنظیم زمان ماهیگیری [دقیقه:ثانیه]</code>",
        "<code>.ماهیگیری روشن</code>",
        "<code>.ماهیگیری خاموش</code>",
    ]
    return "\n".join(lines)

def build_fishing_keyboard(modes: dict) -> InlineKeyboardMarkup:
    rows = []
    for rarity, (emoji, name) in RARITY_LABELS.items():
        mode = modes.get(rarity, "sell")
        memoji, mname = MODE_LABELS[mode]
        rows.append([
            InlineKeyboardButton(
                text=f"{emoji} {name}: {memoji} {mname}",
                callback_data=f"fishmode:{rarity}",
            )
        ])
    rows.append([
        InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="cat_fishing"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_meowie_info"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
