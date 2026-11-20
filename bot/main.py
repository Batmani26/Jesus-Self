"""ربات مدیریت (Management Bot) - Jesus Self"""
import asyncio
import logging
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
import hashlib
import datetime
import pytz
from datetime import datetime
from persiantools.jdatetime import JalaliDate
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram import F
from bot.database import add_user, get_user, set_user_phone, save_session, get_yaqoot, add_yaqoot, get_all_active_users, deduct_yaqoot, deactivate_user, set_user_active
from bot.login import send_code, verify_code, verify_password

import os as _os
BOT_TOKEN = _os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment variables.")

logging.basicConfig(level=logging.INFO)

# Build aiogram session with optional proxy (needed in Iran)
from aiogram.client.session.aiohttp import AiohttpSession as _AioSession
from aiogram.client.telegram import TelegramAPIServer as _TAS
_tg_proxy = _os.getenv("TG_PROXY", "").strip() or None
if _tg_proxy:
    _ai_session = _AioSession(proxy=_tg_proxy, timeout=60)
    bot = Bot(token=BOT_TOKEN, session=_ai_session)
    logging.info(f"Management bot using proxy: {_tg_proxy}")
else:
    bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()


async def _edit_panel(callback, text, kb=None, parse_mode="HTML"):
    """Edit an inline-query panel message safely. Inline messages MUST use inline_message_id."""
    try:
        if getattr(callback, "inline_message_id", None):
            await callback.bot.edit_message_text(
                inline_message_id=callback.inline_message_id,
                text=text, reply_markup=kb, parse_mode=parse_mode,
            )
            return
        if callback.message:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode=parse_mode)
            return
        raise RuntimeError("no message reference available")
    except Exception as e:
        msg = str(e).lower()
        if "message is not modified" in msg:
            return
        raise


# آیدی عددی ادمین (خودت) رو اینجا بذار تا پیام لاگین رو برات بفرسته
# برای پیدا کردن آیدی خودت میتونی از ربات @userinfobot استفاده کنی
ADMIN_ID = int(_os.getenv("ADMIN_ID", "0"))
MAINTENANCE_MODE = False

USER_STATES = {}
CLIENTS = {}
TEMP_CODES = {}
ACTIVE_PANELS = {} # {(chat_id, message_id): user_id}

# Feature toggles (shared with selfbot plugins)
CALC_ENABLED = {"on": True}
TRANS_ENABLED = {"on": True}
GUARDIAN = {
    "deleted": True,
    "selfdestruct": True,
    "edited": True,
}

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✨ ساخت سلف"), KeyboardButton(text="👤 حساب کاربری")],
        [KeyboardButton(text="⚙️ مدیریت سلف")],
        [KeyboardButton(text="📚 راهنما")]
    ],
    resize_keyboard=True
)

CANCEL_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ انصراف")]],
    resize_keyboard=True
)

BACK_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🔙 بازگشت به منوی اصلی")]],
    resize_keyboard=True
)

@dp.inline_query()
async def inline_panel(query: InlineQuery):
    if query.query == "panel" or query.query == "پنل":
        user_id = query.from_user.id
        try:
            balance = await asyncio.wait_for(get_yaqoot(user_id), timeout=1.0)
        except asyncio.TimeoutError:
            balance = 0
        total_seconds = balance * 1800
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        now_utc = datetime.now(pytz.utc)
        now_tehran = now_utc.astimezone(pytz.timezone('Asia/Tehran'))
        time_str = now_tehran.strftime("%H:%M:%S")
        date_miladi = now_tehran.strftime("%Y/%m/%d")
        date_shamsi = JalaliDate(now_tehran).strftime("%Y/%m/%d")
        
        text = (
            "🤖 **پنل کنترل 𝑱𝑬𝑺𝑼𝑺 𝑺𝑬𝑳𝑭**\n\n"
            f"💎 موجودی: **{balance}** یاقوت\n"
            f"⏳ معادل: **{days}** روز، **{hours}** ساعت، **{minutes}** دقیقه، **{seconds}** ثانیه\n"
            f"⏰ ساعت: `{time_str}`\n"
            f"📅 تاریخ شمسی: `{date_shamsi}` | میلادی: `{date_miladi}`\n\n"
            "✨ لطفاً یک قابلیت را از منوی زیر انتخاب کنید:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 بازی ها", callback_data="cat_games"), InlineKeyboardButton(text="🛠 ابزار ها", callback_data="cat_tools")],
            [InlineKeyboardButton(text="⚙️ مدیریت", callback_data="cat_manage"), InlineKeyboardButton(text="🎨 شخصی‌ساز اکانت", callback_data="cat_personalize")],
            [InlineKeyboardButton(text="🛡 استاک و امنیت", callback_data="cat_security"), InlineKeyboardButton(text="🎭 تقلب", callback_data="cat_cheat")],
            [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="refresh_panel"), InlineKeyboardButton(text="❌ بستن پنل", callback_data="feat_close")]
            ])
        result = InlineQueryResultArticle(
            id=hashlib.md5(text.encode()).hexdigest(),
            title="پنل کنترل 𝑱𝑬𝑺𝑼𝑺 𝑺𝑬𝑳𝑭",
            description="برای ارسال پنل کلیک کنید",
            input_message_content=InputTextMessageContent(message_text=text, parse_mode="Markdown"),
            reply_markup=kb
        )
        await query.answer([result], cache_time=0)
        
        # We can't get the message_id from inline query directly. 
        # The userbot will send it, and we track it via the userbot's event.
    else:
        await query.answer([], cache_time=0)

@dp.message(F.via_bot)
async def track_inline_panel(message: Message):
    if message.via_bot and message.via_bot.username == "SelfJesusBot":
        if "پنل کنترل" in message.text:
            ACTIVE_PANELS[(message.chat.id, message.message_id)] = message.from_user.id

async def panel_updater_loop():
    while True:
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Panel updater error: {e}")
        now_utc = datetime.now(pytz.utc)
        now_tehran = now_utc.astimezone(pytz.timezone('Asia/Tehran'))
        time_str = now_tehran.strftime("%H:%M:%S")
        date_miladi = now_tehran.strftime("%Y/%m/%d")
        date_shamsi = JalaliDate(now_tehran).strftime("%Y/%m/%d")
        
        for (chat_id, msg_id), user_id in list(ACTIVE_PANELS.items()):
            try:
                balance = await get_yaqoot(user_id)
                hours = balance // 2
                days = hours // 24
                text = (
                    "🤖 **پنل کنترل 𝑱𝑬𝑺𝑼𝑺 𝑺𝑬𝑳𝑭**\n\n"
                    f"💎 موجودی: **{balance}** یاقوت\n"
                    f"⏳ معادل: **{hours}** ساعت ({days} روز)\n"
                    f"⏰ ساعت: `{time_str}`\n"
                    f"📅 تاریخ شمسی: `{date_shamsi}` | میلادی: `{date_miladi}`\n\n"
                    "✨ لطفاً یک قابلیت را از منوی زیر انتخاب کنید:"
                )
                # NOTE: must re-send inline buttons, otherwise edit strips them
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎮 بازی ها", callback_data="cat_games"), InlineKeyboardButton(text="🛠 ابزار ها", callback_data="cat_tools")],
                    [InlineKeyboardButton(text="⚙️ مدیریت", callback_data="cat_manage"), InlineKeyboardButton(text="🎨 شخصی‌ساز اکانت", callback_data="cat_personalize")],
                    [InlineKeyboardButton(text="🛡 استاک و امنیت", callback_data="cat_security"), InlineKeyboardButton(text="🎭 تقلب", callback_data="cat_cheat")],
                    [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="refresh_panel"), InlineKeyboardButton(text="❌ بستن پنل", callback_data="feat_close")]
                ])
                await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=kb, parse_mode="Markdown")
            except Exception as e:
                if "message is not modified" not in str(e).lower():
                    del ACTIVE_PANELS[(chat_id, msg_id)]

@dp.callback_query(F.data == "refresh_panel")
async def refresh_inline_panel(callback: CallbackQuery):
    user_id = callback.from_user.id
    balance = await get_yaqoot(user_id)
    total_seconds = balance * 1800
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    now_utc = datetime.now(pytz.utc)
    now_tehran = now_utc.astimezone(pytz.timezone('Asia/Tehran'))
    time_str = now_tehran.strftime("%H:%M:%S")
    date_miladi = now_tehran.strftime("%Y/%m/%d")
    date_shamsi = JalaliDate(now_tehran).strftime("%Y/%m/%d")
    
    text = (
        "🤖 **پنل کنترل 𝑱𝑬𝑺𝑼𝑺 𝑺𝑬𝑳𝑭**\n\n"
        f"💎 موجودی: **{balance}** یاقوت\n"
        f"⏳ معادل: **{days}** روز، **{hours}** ساعت، **{minutes}** دقیقه، **{seconds}** ثانیه\n"
        f"⏰ ساعت: `{time_str}`\n"
        f"📅 تاریخ شمسی: `{date_shamsi}` | میلادی: `{date_miladi}`\n\n"
        "✨ لطفاً یک قابلیت را از منوی زیر انتخاب کنید:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 بازی ها", callback_data="cat_games"), InlineKeyboardButton(text="🛠 ابزار ها", callback_data="cat_tools")],
        [InlineKeyboardButton(text="⚙️ مدیریت", callback_data="cat_manage"), InlineKeyboardButton(text="🎨 شخصی‌ساز اکانت", callback_data="cat_personalize")],
        [InlineKeyboardButton(text="🛡 استاک و امنیت", callback_data="cat_security"), InlineKeyboardButton(text="🎭 تقلب", callback_data="cat_cheat")],
        [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="refresh_panel"), InlineKeyboardButton(text="❌ بستن پنل", callback_data="feat_close")]
    ])
    try:
        await _edit_panel(callback, text, kb, parse_mode="Markdown")
        await callback.answer("✅ پنل بروزرسانی شد!")
    except Exception as e:
        if "message is not modified" in str(e).lower():
            await callback.answer("پنل از قبل به‌روز است.", show_alert=True)
        else:
            await callback.answer(f"❌ خطا در بروزرسانی: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("cat_") | F.data.startswith("tool_") | F.data.startswith("tog_") | F.data.startswith("enemy_del:") | (F.data == "curse_list") | (F.data == "back_to_panel"))
async def process_inline_panel_callback(callback: CallbackQuery):
    data_str = callback.data
    if data_str == "cat_casino_info":
        info_text = (
            "🎰 <b>بخش تقلب کازینو</b>\n\n"
            "<blockquote>با استفاده از دستور زیر می‌توانید کازینو تلگرام را مجبور کنید تا به بیشترین امتیاز (جکپات) برسد. کافیست دستور را در هر چتی ارسال کنید.</blockquote>\n\n"
            "<b>دستورات:</b>\n"
            "<code>.کازینو</code> — اسپین معمولی تا امتیاز بالا\n"
            "<code>.کازینو فلک جک</code> — اسپین با سرعت فوق‌العاده بالا تا رسیدن به سه ۷ هم‌سان (جک‌پات) 🎉\n\n"
            "👇 برای کپی، روی دستور کلیک کنید."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_cheat")]
        ])
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "cat_bowling_info":
        info_text = (
            "🎳 <b>بخش تقلب بولینگ</b>\n\n"
            "<blockquote>با استفاده از دستور زیر می‌توانید بولینگ تلگرام را مجبور کنید تا تمام هدف‌ها (Strike) را زمین بیندازد. کافیست دستور را در هر چتی ارسال کنید.</blockquote>\n\n"
            "<b>دستور:</b>\n"
            "<code>.بولینگ</code>\n\n"
            "👇 برای کپی، روی دستور کلیک کنید."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_cheat")]
        ])
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "cat_basketball_info":
        info_text = (
            "🏀 <b>بخش تقلب بسکتبال</b>\n\n"
            "<blockquote>با استفاده از دستور زیر می‌توانید بسکتبال تلگرام را مجبور کنید تا توپ را دقیقاً داخل سبد بیندازد. کافیست دستور را در هر چتی ارسال کنید.</blockquote>\n\n"
            "<b>دستور:</b>\n"
            "<code>.بسکتبال</code>\n\n"
            "👇 برای کپی، روی دستور کلیک کنید."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_cheat")]
        ])
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "cat_dart_info":
        info_text = (
            "🎯 <b>بخش تقلب دارت</b>\n\n"
            "<blockquote>با استفاده از دستور زیر می‌توانید دارت تلگرام را مجبور کنید دقیقاً به وسط هدف (بولزآی) بخورد. کافیست دستور را در هر چتی ارسال کنید.</blockquote>\n\n"
            "<b>دستور:</b>\n"
            "<code>.دارت</code>\n\n"
            "👇 برای کپی، روی دستور کلیک کنید."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_cheat")]
        ])
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "cat_dice_info":
        info_text = (
            "🎲 <b>بخش تقلب تاس</b>\n\n"
            "<blockquote>با استفاده از دستورات زیر می‌توانید تاس تلگرام را مجبور کنید روی عدد دلخواه شما بایستد. کافیست دستور را در هر چتی ارسال کنید.</blockquote>\n\n"
            "<b>دستورات:</b>\n"
            "<code>.تاس 1</code>\n"
            "<code>.تاس 2</code>\n"
            "<code>.تاس 3</code>\n"
            "<code>.تاس 4</code>\n"
            "<code>.تاس 5</code>\n"
            "<code>.تاس 6</code>\n\n"
            "👇 برای کپی، روی هر دستور کلیک کنید."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_cheat")]
        ])
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    cat = data_str.split("_")[1]
    if cat == "games":
        games_text = (
            "🎮 <b>بخش بازی‌ها</b>\n\n"
            "بازی مورد نظر خود را انتخاب کنید:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🐱 میویی", callback_data="cat_meowie_info")],
            [InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="back_to_panel")]
        ])
        try:
            await _edit_panel(callback, games_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "cat_meowie_info":
        meowie_text = (
            "🐱 <b>بخش میویی</b>\n\n"
            "قابلیت مورد نظر را انتخاب کنید:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 میو خودکار", callback_data="cat_meow_auto")],
            [InlineKeyboardButton(text="🐈 نجات پیشی", callback_data="cat_save_cat")],
            [InlineKeyboardButton(text="🎣 ماهیگیری", callback_data="cat_fishing")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_games")]
        ])
        try:
            await _edit_panel(callback, meowie_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "cat_fishing" or data_str.startswith("cat_fishmode:"):
        if data_str.startswith("cat_fishmode:"):
            rarity = data_str.split(":", 1)[1]
            from bot.database import get_fish_modes as _g, set_fish_mode
            _order = ["sell", "cat", "fridge"]
            try:
                _m = await _g(callback.from_user.id)
                _c = _m.get(rarity, "sell")
                _n = _order[(_order.index(_c) + 1) % len(_order)]
                await set_fish_mode(callback.from_user.id, rarity, _n)
                await callback.answer()
            except Exception as exc:
                await callback.answer(f"خطا: {exc}", show_alert=True)
        from bot.database import get_meow_target_db, get_fishing_active, get_fishing_interval
        try:
            target = await get_meow_target_db(callback.from_user.id)
            is_active = await get_fishing_active(callback.from_user.id)
            interval = await get_fishing_interval(callback.from_user.id)
            
            target_text = f"📍 مقصد فعلی: <b>{target['chat_title']}</b>" if target else "⚠️ مقصدی تنظیم نشده است."
            status_text = "🟢 فعال (مشغول)" if is_active else "🔴 غیرفعال (بیکار)"
            interval_display = interval if interval else "تنظیم نشده"
        except Exception as e:
            target_text = f"⚠️ خطا: {e}"
            status_text = "نامشخص"
            interval_display = "نامشخص"
            
        from bot.database import get_fish_modes
        from bot.fish_panel import build_fishing_text, build_fishing_keyboard
        try:
            modes = await get_fish_modes(callback.from_user.id)
        except Exception:
            modes = {}
        info_text = build_fishing_text(target_text, status_text, interval_display, modes)
        kb = build_fishing_keyboard(modes)
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "cat_fishing":
        from bot.database import get_meow_target_db, get_fishing_active, get_fishing_interval
        try:
            target = await get_meow_target_db(callback.from_user.id)
            is_active = await get_fishing_active(callback.from_user.id)
            interval = await get_fishing_interval(callback.from_user.id)
            
            target_text = f"📍 مقصد فعلی: <b>{target['chat_title']}</b>" if target else "⚠️ مقصدی تنظیم نشده است."
            status_text = "🟢 فعال (مشغول)" if is_active else "🔴 غیرفعال (بیکار)"
            interval_display = interval if interval else "تنظیم نشده"
        except Exception as e:
            target_text = f"⚠️ خطا: {e}"
            status_text = "نامشخص"
            interval_display = "نامشخص"
            
        from bot.database import get_fish_modes
        from bot.fish_panel import build_fishing_text, build_fishing_keyboard
        try:
            modes = await get_fish_modes(callback.from_user.id)
        except Exception:
            modes = {}
        info_text = build_fishing_text(target_text, status_text, interval_display, modes)
        kb = build_fishing_keyboard(modes)
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str.startswith("cat_fishmode:"):
        rarity = data_str.split(":", 1)[1]
        from bot.database import get_fish_modes, set_fish_mode
        order = ["sell", "cat", "fridge"]
        try:
            modes = await get_fish_modes(callback.from_user.id)
            cur = modes.get(rarity, "sell")
            nxt = order[(order.index(cur) + 1) % len(order)]
            await set_fish_mode(callback.from_user.id, rarity, nxt)
            await callback.answer(f"{rarity} -> {nxt}")
        except Exception as exc:
            await callback.answer(f"خطا: {exc}", show_alert=True)
        data_str = "cat_fishing"

    if data_str == "cat_save_cat":
        from selfbot.plugins.save_cat import SAVE_CAT_STATUS
        status_text = "🟢 فعال (مشغول)" if SAVE_CAT_STATUS["active"] else "🔴 غیرفعال"
        if SAVE_CAT_STATUS["scanning"]:
            status_text = "🔍 در حال جستجو..."
        announce_text = ("🟢 فعال") if SAVE_CAT_STATUS.get("announce", False) else ("🔴 غیرفعال")
            
        info_text = (
            "🐈 <b>نجات پیشی</b>\n\n"
            f"📊 <b>وضعیت:</b> {status_text}\n\n"
            f"📢 <b>اعلام نجات:</b> {announce_text}\n\n"
            "<blockquote>با فعال کردن این قابلیت، سلف‌بات به صورت خودکار روی دکمه «نجات پیشی» در پیام‌های ربات میویی کلیک می‌کند تا گربه‌ها را نجات دهد.</blockquote>\n\n"
            "<b>دستورات:</b>\n"
            "<code>.نجات پیشی روشن</code> (برای شروع)\n"
            "<code>.نجات پیشی خاموش</code> (برای توقف)\n"
            "<code>.نجات در تمامی چت ها</code> (جستجوی همه گروه‌ها)\n"
            "<code>.اعلام نجات [روشن/خاموش]</code> (اعلام در Saved Messages)\n\n"
            "👇 برای کپی، روی هر دستور کلیک کنید."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="cat_save_cat")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_meowie_info")]
        ])
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "cat_meow_auto":
        from bot.database import get_meow_target_db, get_meow_active, get_meow_interval
        try:
            target = await get_meow_target_db(callback.from_user.id)
            interval = await get_meow_interval(callback.from_user.id)
            is_active = await get_meow_active(callback.from_user.id) and bool(interval)
            if target:
                status_text = "🟢 فعال (مشغول)" if is_active else "🔴 غیرفعال (بیکار)"
                target_text = f"📍 مقصد فعلی: <b>{target['chat_title']}</b>\n📊 وضعیت: {status_text}"
            else:
                target_text = "⚠️ مقصدی تنظیم نشده است."
        except Exception as e:
            target_text = f"⚠️ خطا در خواندن مقصد: {e}"
        
        interval_display = interval if interval else "تنظیم نشده"
        info_text = (
            "🤖 <b>میو خودکار</b>\n\n"
            "<blockquote>با استفاده از این قابلیت، می‌توانید در گروه‌هایی که ربات میویی وجود دارد، به صورت خودکار کلمه «میو» را ارسال کنید تا امتیاز جمع کنید.</blockquote>\n\n"
            f"{target_text}\n"
            f"⏱ تایم تنظیم شده: <b>{interval_display}</b>\n\n"
            "<b>مراحل:</b>\n"
            "1️⃣ ابتدا در گروه مورد نظر دستور <code>.تنظیم میویی</code> را بزنید.\n"
            "2️⃣ تایم کول‌داون خود را تنظیم کنید: <code>.تنظیم زمان میویی [دقیقه:ثانیه]</code>\n"
            "3️⃣ سپس دستور <code>.میو روشن</code> را بزنید.\n\n"
            "<b>دستور توقف:</b>\n"
            "<code>.میو خاموش</code>\n\n"
            "👇 برای کپی، روی هر دستور کلیک کنید."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_meowie_info")]
        ])
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return
    elif cat == "tools":
        tools_text = (
            "🛠 <b>بخش ابزارها</b>\n\n"
            "ابزار مورد نظر خود را انتخاب کنید:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧠 هوش مصنوعی (جیزس)", callback_data="tool_ai_info")],
            [InlineKeyboardButton(text="🧮 ماشین حساب", callback_data="tool_calc_info"), InlineKeyboardButton(text="🌐 ترجمه", callback_data="tool_translate_info")],
            [InlineKeyboardButton(text="🛡 نگهبان چت", callback_data="tool_guardian_info")],
            [InlineKeyboardButton(text="☠️ دشمنان", callback_data="tool_enemies_info")],
            [InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="back_to_panel")]
        ])
        try:
            await _edit_panel(callback, tools_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str in ("tool_calc_info", "tog_calc"):
        from bot.database import get_feature_flags, toggle_feature
        if data_str == "tog_calc":
            await toggle_feature(callback.from_user.id, "calc_on")
        flags = await get_feature_flags(callback.from_user.id)
        on = flags.get("calc_on", True)
        st = "🟢 روشن" if on else "🔴 خاموش"
        btn = "🔴 خاموش کن" if on else "🟢 روشن کن"
        info_text = (
            "🧮 <b>ماشین حساب خودکار</b>\n\n"
            f"وضعیت شما: <b>{st}</b>\n\n"
            "<blockquote>وقتی روشن باشد، هر پیامی که شامل عملگر + - * / باشد، خودکار حل می‌شود و نتیجه به همان پیام اضافه می‌شود.</blockquote>\n\n"
            "<b>مثال‌ها:</b>\n"
            "<code>5+3</code> → 8\n"
            "<code>145+3+6+158*3</code> → 628\n"
            "<code>(7-2)/5</code> → 1\n\n"
            "👇 دکمه پایین برای روشن/خاموش کردن (فقط برای حساب شما):"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn, callback_data="tog_calc")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_tools")]
        ])
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "curse_list":
        from bot.database import get_curses
        try:
            curses = await get_curses(callback.from_user.id)
        except Exception:
            curses = []
        if curses:
            lines = ["📜 <b>لیست فحش‌های شما:</b>", ""]
            for i, c in enumerate(curses[:50], 1):
                lines.append(f"{i}. <blockquote>{c}</blockquote>")
        else:
            lines = ["📜 <b>لیست فحش‌های شما خالی است.</b>", "", "با دستور <code>.افزودن فحش [متن]</code> اضافه کنید."]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="tool_enemies_info")]
        ])
        info_text = "\n".join(lines)
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "tool_translate_info":
        st = "🟢 روشن" if TRANS_ENABLED.get("on", True) else "🔴 خاموش"
        info_text = (
            "🌐 <b>مترجم هوشمند (تشخیص زبان)</b>\n\n"
            f"وضعیت: <b>{st}</b>\n\n"
            "<blockquote>متن انگلیسی بفرست → به فارسی ترجمه می‌شود.\n"
            "متن فارسی بفرست → به انگلیسی ترجمه می‌شود.\n"
            "روی ریپلای هم کار می‌کند و پیام خودت را ویرایش می‌کند.</blockquote>\n\n"
            "<b>دستور:</b>\n"
            "<code>.ترجمه Hello World</code>\n"
            "<code>.ترجمه سلام دنیا</code>\n\n"
            "👇 دکمه پایین برای روشن/خاموش کردن:"
        )
        btn = "🔴 خاموش کن" if TRANS_ENABLED.get("on", True) else "🟢 روشن کن"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn, callback_data="tog_translate")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_tools")]
        ])
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "tog_translate":
        TRANS_ENABLED["on"] = not TRANS_ENABLED.get("on", True)
        st = "🟢 روشن" if TRANS_ENABLED["on"] else "🔴 خاموش"
        btn = "🔴 خاموش کن" if TRANS_ENABLED["on"] else "🟢 روشن کن"
        info_text = (
            "🌐 <b>مترجم هوشمند</b>\n\n"
            f"وضعیت: <b>{st}</b>\n\n"
            "<blockquote>متن انگلیسی بفرست → فارسی.\n"
            "متن فارسی بفرست → انگلیسی.</blockquote>\n\n"
            "<b>دستور:</b>\n"
            "<code>.ترجمه Hello World</code>\n"
            "<code>.ترجمه سلام دنیا</code>\n\n"
            "👇 دکمه پایین برای روشن/خاموش کردن:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn, callback_data="tog_translate")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_tools")]
        ])
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "tool_enemies_info" or data_str.startswith("enemy_del:"):
        from bot.database import get_enemies, remove_enemy
        if data_str.startswith("enemy_del:"):
            try:
                eid = int(data_str.split(":", 1)[1])
                await remove_enemy(callback.from_user.id, eid)
                await callback.answer("✅ دشمن از لیست حذف شد")
            except Exception as exc:
                await callback.answer(f"خطا: {exc}", show_alert=True)
        try:
            enemies = await get_enemies(callback.from_user.id)
        except Exception:
            enemies = []
        lines = [
            "☠️ <b>بخش دشمنان</b>",
            "",
            "<blockquote>هر شخصی که به لیست دشمنان اضافه کنی، با دیدن هر پیام او در پیوی یا گروه، سلف یک فحش از لیست فحش‌های تو به او می‌دهد.</blockquote>",
            "",
            "<b>📖 آموزش:</b>",
            "1️⃣ روی پیام شخص ریپلای کن و بزن <code>.تنظیم دشمن</code>",
            "💡 یا بدون ریپلای: <code>.تنظیم دشمن @username</code> یا <code>.تنظیم دشمن 123456789</code>",
            "2️⃣ فحش دلخواه اضافه کن: <code>.افزودن فحش [متن]</code>",
            "3️⃣ باقی‌اش را به ما بسپارید.",
            "",
            "<b>✏️ حذف دشمن:</b> با <code>.حذف دشمن @user</code> یا ریپلای + <code>.حذف دشمن</code>",
            "<b>🧹 پاکسازی فحش‌ها:</b> <code>.پاکسازی لیست فحش</code>",
            "",
        ]
        if enemies:
            lines.append(f"<b>👥 لیست دشمنان شما ({len(enemies)}):</b>")
        else:
            lines.append("<b>👥 لیست دشمنان شما:</b> هنوز خالی است.")
        kb_rows = [[InlineKeyboardButton(text="📜 فحش‌های من", callback_data="curse_list")]]
        for e in enemies[:30]:
            nm = e["enemy_name"] or "نامشخص"
            kb_rows.append([InlineKeyboardButton(text=f"🗑 {nm} ({e['enemy_id']})", callback_data=f"enemy_del:{e['enemy_id']}")])
        kb_rows.append([InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="tool_enemies_info")])
        kb_rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_tools")])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
        info_text = "\n".join(lines)
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "cat_manage":
        from bot.database import get_setting as _gs
        try:
            _lp = await _gs(callback.from_user.id, "lock_pv", 0)
            _so = await _gs(callback.from_user.id, "secretary_on", 0)
            _stx = await _gs(callback.from_user.id, "secretary_text") or "تنظیم نشده"
        except Exception:
            _lp, _so, _stx = 0, 0, "تنظیم نشده"
        _lp_s = "🟢 فعال" if _lp else "🔴 غیرفعال"
        _so_s = "🟢 روشن" if _so else "🔴 خاموش"
        info_text = (
            "⚙️ <b>بخش مدیریت</b>\n\n"
            f"📊 <b>وضعیت فعلی:</b>\n"
            f"┣ 🔒 قفل پیوی: {_lp_s}\n"
            f"┣ 🤖 منشی: {_so_s}\n"
            f"┗ ✉️ متن منشی: <i>{_stx}</i>\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🗑 <b>حذف پیام</b>\n"
            "<blockquote>روی پیام موردنظر ریپلای کن و <code>.حذف</code> بزن تا پیام برای هر دو طرف حذف شود.\n"
            "برای پاک‌سازی گروهی: <code>.حذف 100</code> (بین ۱ تا ۱۰۰ پیام).\n"
            "در گروه‌های تاپیک‌دار فقط همان تاپیک پاک می‌شود.</blockquote>\n\n"
            "🧹 <b>پاک‌سازی کامل تاپیک</b>\n"
            "<blockquote>داخل هر تاپیکی بنویس <code>.پاکسازی تاپیک</code> تا همه پیام‌های همان تاپیک (بدون سقف) حذف شوند. تاپیک‌های دیگر دست‌نخورده می‌مانند.</blockquote>\n\n"
            "🔇 <b>سکوت کاربر</b>\n"
            "<blockquote>روی پیام کاربر ریپلای کن و <code>.سکوت</code> بزن. از آن پس هر پیام او فوراً حذف می‌شود.\n"
            "برای آزادسازی: <code>.حذف سکوت</code></blockquote>\n\n"
            "🔒 <b>قفل پیوی</b>\n"
            "<blockquote><code>.قفل پیوی</code> — روشن/خاموش\n"
            "<code>.بازکردن قفل پیوی</code> — قطعاً غیرفعال\n"
            "وقتی فعال باشد، هر پیام ورودی در پیوی حذف می‌شود.</blockquote>\n\n"
            "🤖 <b>منشی خودکار</b>\n"
            "<blockquote>1️⃣ <code>.تنظیم متن منشی [متن]</code>\n"
            "2️⃣ <code>.منشی روشن</code> یا <code>.منشی خاموش</code>\n"
            "سلف به‌طور خودکار به پیام‌های ورودی در پیوی پاسخ می‌دهد.</blockquote>\n\n"
            "💥 <b>اسپم</b>\n"
            "<blockquote><code>.اسپم متن 50</code> — متن را ۵۰ بار (۱..۱۰۰) در همین چت می‌فرستد و در پایان اعلام می‌کند.</blockquote>\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "👇 روی هر دستور کلیک کن تا کپی شود."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 بروزرسانی وضعیت", callback_data="cat_manage")],
            [InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="back_to_panel")]
        ])
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "cat_personalize" or data_str.startswith("pers_tog:"):
        from bot.database import get_setting, toggle_setting
        if data_str.startswith("pers_tog:"):
            col = data_str.split(":", 1)[1]
            try:
                await toggle_setting(callback.from_user.id, col)
                await callback.answer("✅ تغییر کرد")
            except Exception as e:
                await callback.answer(f"خطا: {e}", show_alert=True)
        ao = await get_setting(callback.from_user.id, "always_online", 0)
        at = await get_setting(callback.from_user.id, "always_typing", 0)
        def _st(v):
            return "روشن 🟢" if v else "خاموش 🔴"
        info_text = (
            "🎨 <b>شخصی‌ساز اکانت</b>\n\n"
            f"📊 <b>وضعیت فعلی:</b> آنلاین {_st(ao)} | در حال نوشتن {_st(at)}\n\n"
            "<b>📖 آموزش:</b>\n"
            "🟢 <b>همیشه آنلاین</b>\n<blockquote>وقتی روشن باشد، اکانت شما هرگز آفلاین نمی‌شود.</blockquote>\n"
            "✍️ <b>همیشه در حال نوشتن</b>\n<blockquote>در گروه‌ها همیشه حالت «در حال نوشتن...» نمایش داده می‌شود.</blockquote>\n\n"
            "👇 با دکمه‌ها وضعیت را تغییر بده:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🟢 همیشه آنلاین: {_st(ao)}", callback_data="pers_tog:always_online")],
            [InlineKeyboardButton(text=f"✍️ همیشه در حال نوشتن: {_st(at)}", callback_data="pers_tog:always_typing")],
            [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="cat_personalize")],
            [InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="back_to_panel")]
        ])
        try:
            await _edit_panel(callback, info_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "back_to_panel":
        from bot.database import get_yaqoot as _gy
        balance = await _gy(callback.from_user.id)
        total_seconds = balance * 1800
        _days = total_seconds // 86400
        _hours = (total_seconds % 86400) // 3600
        _mins = (total_seconds % 3600) // 60
        _secs = total_seconds % 60
        _now_utc = datetime.now(pytz.utc)
        _now_t = _now_utc.astimezone(pytz.timezone('Asia/Tehran'))
        _tstr = _now_t.strftime("%H:%M:%S")
        _dm = _now_t.strftime("%Y/%m/%d")
        try:
            _ds = JalaliDate(_now_t).strftime("%Y/%m/%d")
        except Exception:
            _ds = _dm
        text = (
            "🤖 **پنل کنترل 𝑱𝑬𝑺𝑼𝑺 𝑺𝑬𝑳𝑭**\n\n"
            f"💎 موجودی: **{balance}** یاقوت\n"
            f"⏳ معادل: **{_days}** روز، **{_hours}** ساعت، **{_mins}** دقیقه، **{_secs}** ثانیه\n"
            f"⏰ ساعت: `{_tstr}`\n"
            f"📅 تاریخ شمسی: `{_ds}` | میلادی: `{_dm}`\n\n"
            "✨ لطفاً یک قابلیت را از منوی زیر انتخاب کنید:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 بازی ها", callback_data="cat_games"), InlineKeyboardButton(text="🛠 ابزار ها", callback_data="cat_tools")],
            [InlineKeyboardButton(text="⚙️ مدیریت", callback_data="cat_manage"), InlineKeyboardButton(text="🎨 شخصی‌ساز اکانت", callback_data="cat_personalize")],
            [InlineKeyboardButton(text="🛡 استاک و امنیت", callback_data="cat_security"), InlineKeyboardButton(text="🎭 تقلب", callback_data="cat_cheat")],
            [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="refresh_panel"), InlineKeyboardButton(text="❌ بستن پنل", callback_data="feat_close")]
        ])
        try:
            await _edit_panel(callback, text, kb, parse_mode="Markdown")
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str == "tool_ai_info":
        info_text = (
            "🧠✨ <b>هوش مصنوعی جیزس (Jesus AI)</b> ✨🧠\n\n"
            "<blockquote>یک مغز دیجیتال فوق‌سریع که فکر می‌کند، جستجو می‌کند، عکس می‌آورد و لحظه‌ای جواب می‌دهد — انگار یک نابغه ۲۴ ساعته کنارته! 🚀</blockquote>\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🎯 <b>دستور جادویی:</b>\n"
            "<code>.جیزس [هر چیزی که می‌خوای]</code>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "🌟 <b>جیزس چه کارهایی بلده؟</b>\n\n"
            "💬 <b>گپ دوستانه و خلاقانه</b>\n"
            "هر سوالی داری بپرس — از فلسفه تا شوخی!\n"
            "<code>.جیزس یه جوک بامزه بگو</code>\n"
            "<code>.جیزس یک شعر عاشقانه بنویس</code>\n\n"
            "💻 <b>برنامه‌نویس حرفه‌ای</b>\n"
            "کد بنویس، باگ پیدا کن، توضیح بده.\n"
            "<code>.جیزس یه اسکریپت پایتون برای دانلود عکس بنویس</code>\n"
            "<code>.جیزس این خطا رو حل کن: IndexError</code>\n\n"
            "💎 <b>قیمت‌های لحظه‌ای (زنده از بازار)</b>\n"
            "دلار، یورو، طلا، سکه، بیت‌کوین — مستقیم از TGJU!\n"
            "<code>.جیزس قیمت دلار به تومان</code>\n"
            "<code>.جیزس قیمت طلای ۱۸ عیار</code>\n"
            "<code>.جیزس سکه امامی چنده</code>\n\n"
            "📰 <b>خبرنگار شخصی تو</b>\n"
            "آخرین اخبار، نتایج ورزشی، اتفاقات روز.\n"
            "<code>.جیزس آخرین اخبار تکنولوژی</code>\n"
            "<code>.جیزس نتیجه بازی رئال</code>\n"
            "<code>.جیزس هوا تهران فردا چطوره</code>\n\n"
            "📝 <b>نویسنده و خلاصه‌ساز</b>\n"
            "<code>.جیزس یه کپشن برای این عکس بنویس</code>\n"
            "<code>.جیزس این متن طولانی رو خلاصه کن</code>\n\n"
            "🎓 <b>معلم خصوصی</b>\n"
            "<code>.جیزس قانون نیوتن رو ساده توضیح بده</code>\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💡 <b>نکته:</b> هرچه سؤالت واضح‌تر باشه، جواب دقیق‌تره!\n\n"
            "👇 روی هر دستور کلیک کن تا کپی شه و بفرست."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_tools")]
        ])
        try:
            if callback.message:
                await callback.message.edit_text(info_text, reply_markup=kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    if data_str in ("tool_guardian_info", "tog_g_deleted", "tog_g_selfdestruct", "tog_g_edited"):
        if data_str == "tog_g_deleted":
            GUARDIAN["deleted"] = not GUARDIAN.get("deleted", True)
        elif data_str == "tog_g_selfdestruct":
            GUARDIAN["selfdestruct"] = not GUARDIAN.get("selfdestruct", True)
        elif data_str == "tog_g_edited":
            GUARDIAN["edited"] = not GUARDIAN.get("edited", True)
        def _st(v):
            return "🟢 روشن" if v else "🔴 خاموش"
        def _lbl(v):
            return "🔴 خاموش کن" if v else "🟢 روشن کن"
        d, s, e = GUARDIAN.get("deleted", True), GUARDIAN.get("selfdestruct", True), GUARDIAN.get("edited", True)
        info_text = (
            "🛡 <b>نگهبان چت (Chat Guardian)</b>\n\n"
            "<blockquote>از پیام‌هایت محافظت می‌کند: پیام‌های حذف‌شده، رسانه‌های نابودشونده و پیام‌های ویرایش‌شده را در «پیام‌های ذخیره‌شده» نگه می‌دارد.</blockquote>\n\n"
            "━━━━━━━━━━━━━━\n"
            "🗑 <b>سیو پیام حذف شده</b>\n"
            f"وضعیت: {_st(d)}\n"
            "<blockquote>اگر کسی در پیوی تو پیامی بفرستد و بعد حذفش کند، سلف آن را فوراً در Saved Messages فوروارد می‌کند.</blockquote>\n\n"
            "💥 <b>سیو مدیای نابود شونده</b>\n"
            f"وضعیت: {_st(s)}\n"
            "<blockquote>عکس/ویدیوی نابودشونده (self-destruct) که برایت می‌فرستند، بلافاصله ذخیره و به Saved Messages ارسال می‌شود.</blockquote>\n\n"
            "✏️ <b>سیو پیام ویرایش شده</b>\n"
            f"وضعیت: {_st(e)}\n"
            "<blockquote>اگر پیامی ویرایش شود، نسخه قبلی و متن جدید در Saved Messages ذخیره می‌شود.</blockquote>\n\n"
            "━━━━━━━━━━━━━━\n"
            "👇 برای روشن/خاموش کردن هر بخش روی دکمه‌اش بزن:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🗑 سیو پیام حذف شده — {_lbl(d)}", callback_data="tog_g_deleted")],
            [InlineKeyboardButton(text=f"💥 سیو مدیای نابود شونده — {_lbl(s)}", callback_data="tog_g_selfdestruct")],
            [InlineKeyboardButton(text=f"✏️ سیو پیام ویرایش شده — {_lbl(e)}", callback_data="tog_g_edited")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="cat_tools")]
        ])
        try:
            if callback.message:
                await callback.message.edit_text(info_text, reply_markup=kb)
            await callback.answer("✅ ذخیره شد" if data_str != "tool_guardian_info" else None)
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)
        return

    elif cat == "fun":
        await callback.answer("👁 بخش نظارت و سرگرمی (به‌زودی)", show_alert=True)
    elif cat == "cheat":
        cheat_text = (
            "🎭 <b>بخش تقلب (بازی‌های شانسی)</b>\n\n"
            "یکی از بازی‌های زیر را انتخاب کنید. (نتیجه کاملاً تصادفی است)\n"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎲 تاس", callback_data="cat_dice_info"), InlineKeyboardButton(text="🎯 دارت", callback_data="cat_dart_info")],
            [InlineKeyboardButton(text="🏀 بسکتبال", callback_data="cat_basketball_info"), InlineKeyboardButton(text="🎳 بولینگ", callback_data="cat_bowling_info")],
            [InlineKeyboardButton(text="🎰 کازینو", callback_data="cat_casino_info")],
            [InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="back_to_panel")]
        ])
        try:
            await _edit_panel(callback, cheat_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)

    elif cat == "security":
        guide_text = (
            "🛡 <b>بخش استاک و امنیت</b>\n\n"
            "<blockquote>سلف ما قابلیتی برای کاربران هموار ساخته که با استفاده از آیدی عددی و یا یوزرنیم شخص، اطلاعاتی از اکانت مورد نظر را به شما نشان دهد.</blockquote>\n\n"
            "<blockquote>جهت استفاده از این قابلیت، شما با ارسال .استاک یک پیامی در سیو مسیج خود دریافت می‌کنید که منتظر دریافت آیدی عددی و یا یوزرنیم از طرف شما است و شما با ارسال آن، اطلاعاتی را در همان سیو مسیج دریافت می‌کنید.</blockquote>\n\n"
            "👇 برای کپی کردن دستور، روی آن کلیک کنید:"
        )
        from aiogram.types import CopyTextButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 کپی دستور", copy_text=CopyTextButton(text=".استاک"))],
            [InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="back_to_panel")]
        ])
        try:
            await _edit_panel(callback, guide_text, kb)
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("game_"))
async def process_dice_games(callback: CallbackQuery):
    game = callback.data.split("_")[1]
    emojis = {
        "dice": "🎲",
        "dart": "🎯",
        "basketball": "🏀",
        "bowling": "🎳",
        "casino": "🎰"
    }
    if game in emojis:
        try:
            await callback.bot.send_dice(chat_id=callback.from_user.id, emoji=emojis[game])
        except Exception:
            if callback.message:
                await callback.message.answer_dice(emoji=emojis[game])
        await callback.answer()

@dp.callback_query(F.data == "copy_stalk")
async def cb_copy_stalk(callback: CallbackQuery):
    if callback.message:
        await callback.message.reply("کد کپی شد: `.استاک`", parse_mode="Markdown")
    await callback.answer("✅ دستور کپی شد!", show_alert=True)

# back_to_panel is handled inside process_inline_panel_callback
# (removed duplicate + broken handler that caused SyntaxError)

@dp.callback_query(F.data == "feat_close")
async def close_inline_panel(callback: CallbackQuery):
    try:
        if callback.message:
            await callback.message.delete()
        else:
            await callback.bot.edit_message_text(
                inline_message_id=callback.inline_message_id,
                text="✅ **پنل با موفقیت بسته شد.**",
                reply_markup=None,
                parse_mode="Markdown"
            )
    except Exception as e:
        await callback.answer(f"خطا در بستن: {e}", show_alert=True)
        return
    await callback.answer("✅ پنل با موفقیت بسته شد.", show_alert=True)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if MAINTENANCE_MODE and message.from_user.id != ADMIN_ID:
        await message.answer("⚠️ **ربات موقتاً خاموش است.**\n\nلطفاً بعداً تلاش کنید.")
        return
    await add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    
    caption = (
        f"سلام **{message.from_user.first_name}** عزیز! 👋\n\n"
        "به دنیای **𝑱𝑬𝑺𝑼𝑺 𝑺𝑬𝑳𝑭** خوش آمدی! 🚀\n\n"
        "✨ اینجا می‌تونی سلف‌بات اختصاصی خودت رو بسازی و از تمام امکاناتش لذت ببری.\n\n"
        "👇 از منوی زیر انتخاب کن:"
    )
    
    # به جای لینک، می‌تونی آدرس عکسی که می‌خوای رو اینجا بذاری
    photo_url = "https://uploadkon.ir/uploads/d49214_26Heavenly-Jesus-Self-Promo-Banner.png"
    
    try:
        await message.answer_photo(photo=photo_url, caption=caption, reply_markup=MAIN_KEYBOARD, parse_mode="Markdown")
    except Exception:
        await message.answer(caption, reply_markup=MAIN_KEYBOARD, parse_mode="Markdown")

@dp.message(Command("users"))
async def cmd_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    users = await get_all_active_users()
    if not users:
        await message.answer("هیچ کاربر فعالی یافت نشد.")
        return
    text = "👥 **کاربران لاگین شده:**\n\n"
    for u in users:
        text += f"👤 {u['first_name']} | 🆔 `{u['user_id']}`\n📱 {u['phone_number']} | 💎 {u['yaqoot_balance']}\n➖➖➖➖➖\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ شما دسترسی به این دستور را ندارید.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("استفاده: `/broadcast متن پیام`", parse_mode="Markdown")
        return
    body = parts[1]
    users = await get_all_active_users()
    sent, failed = 0, 0
    status = await message.answer(f"📤 در حال ارسال به {len(users)} کاربر...")
    for u in users:
        try:
            await bot.send_message(u['user_id'], body, parse_mode="Markdown")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await status.edit_text(f"✅ ارسال شد: {sent}{NL}❌ ناموفق: {failed}")


@dp.message(Command("apology"))
async def cmd_apology(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ شما دسترسی به این دستور را ندارید.")
        return
    await message.answer("⏳ در حال ارسال اطلاعیه...")
    apology = (
        "🙏 **اطلاعیهٔ رسمی Jesus Self**" + NL + NL
        + "کاربر گرامی،" + NL + NL
        + "در راستای **افزایش امنیت حساب و سلف‌بات شما**، کلید رمزنگاری سشن‌ها به‌روزرسانی شد." + NL
        + "به همین دلیل، سشن‌های ذخیره‌شدهٔ قبلی قابل بازیابی نیستند و لازم است **یک بار** دوباره وارد حساب خود شوید." + NL + NL
        + "🔒 این تغییر برای **محافظت از اطلاعات شما** انجام شده است." + NL
        + "⏱ فرایند ورود کمتر از ۱ دقیقه طول می‌کشد و بعد از آن، دیگر نیازی به ورود مجدد نیست." + NL + NL
        + "با تشکر از همراهی شما 🌹" + NL
        + "تیم Jesus Self"
    )
    users = await get_all_active_users()
    sent, failed = 0, 0
    status = await message.answer(f"📤 در حال ارسال اطلاعیه به {len(users)} کاربر...")
    for u in users:
        try:
            await bot.send_message(u['user_id'], apology, parse_mode="Markdown")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await status.edit_text(f"✅ ارسال شد: {sent}{NL}❌ ناموفق: {failed}")


@dp.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ شما دسترسی به این دستور را ندارید.")
        return

    # Text after /broadcast (or use replied message text/media)
    parts = (message.text or "").split(maxsplit=1)
    payload = parts[1].strip() if len(parts) > 1 else ""
    replied = message.reply_to_message
    if not payload and replied and (replied.text or replied.caption):
        payload = (replied.text or replied.caption or "").strip()
    if not payload and not (replied and (replied.photo or replied.video or replied.document)):
        await message.answer(
            "⚠️ فرمت صحیح:\n"
            "`/broadcast [متن پیام]`\n"
            "یا روی یک پیام (متن/عکس/ویدیو/فایل) ریپلای کن و `/broadcast` بزن.",
            parse_mode="Markdown",
        )
        return

    status = await message.answer("⏳ در حال ارسال به همه کاربران...")
    users = await get_all_active_users()
    ids = {u["user_id"] for u in users}
    if ADMIN_ID:
        ids.add(ADMIN_ID)

    # Auto-detect formatting: Telegram bold (<b>/<strong>) or HTML tag => HTML mode;
    # `**bold**` => Markdown; otherwise plain text. This prevents parse errors.
    low = payload.lower()
    if any(t in low for t in ("<b>", "<i>", "<u>", "<s>", "<a ", "<code>", "<pre>", "<blockquote>")):
        parse_mode = "HTML"
    elif "**" in payload or "__" in payload or "`" in payload:
        parse_mode = "Markdown"
    else:
        parse_mode = None

    async def _send_one(uid):
        if replied and (replied.photo or replied.video or replied.document):
            await bot.copy_message(chat_id=uid, from_chat_id=replied.chat.id, message_id=replied.message_id)
            return
        try:
            await bot.send_message(uid, payload, parse_mode=parse_mode)
        except Exception:
            # Fallback to plain text if formatting is invalid
            await bot.send_message(uid, payload)

    sent = 0
    failed = 0
    for uid in ids:
        try:
            await _send_one(uid)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await status.edit_text(
        f"✅ <b>ارسال نسخهٔ جدید به پایان رسید</b>\n\n"
        f"📬 موفق: <code>{sent}</code>\n❌ ناموفق: <code>{failed}</code>\n👥 کل: <code>{len(ids)}</code>",
        parse_mode="HTML",
    )


@dp.message(Command("charge"))
async def cmd_charge(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ شما دسترسی به این دستور را ندارید.")
        return
    
    args = message.text.split()
    if len(args) != 3:
        await message.answer("⚠️ فرمت صحیح:\n`/charge <user_id> <amount>`\nمثال: `/charge 123456789 50`", parse_mode="Markdown")
        return
        
    try:
        target_id = int(args[1])
        amount = int(args[2])
    except ValueError:
        await message.answer("⚠️ آیدی و مقدار باید عدد باشند.")
        return
        
    await add_yaqoot(target_id, amount)
    await message.answer(f"✅ **{amount}** یاقوت به کاربر `{target_id}` اضافه شد.", parse_mode="Markdown")
    try:
        msg = (
            "💎✨ **شارژ حساب با موفقیت انجام شد!** ✨💎\n\n"
            f"🎁 مقدار **{amount}** یاقوت به کیف پول شما واریز شد.\n\n"
            "🚀 حالا می‌توانید از تمام امکانات **𝑱𝑬𝑺𝑼𝑺 𝑺𝑬𝑳𝑭** لذت ببرید!\n"
            "📊 برای مشاهده موجودی و زمان باقیمانده به بخش «حساب کاربری» بروید."
        )
        await bot.send_message(target_id, msg, parse_mode="Markdown")
    except Exception:
        pass

@dp.message(F.text == "⚙️ مدیریت سلف")
async def cb_manage_self(message: Message):
    user_id = message.from_user.id
    text, kb = await build_manage_text(user_id)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

async def build_manage_text(user_id):
    user = await get_user(user_id)
    balance = await get_yaqoot(user_id)
    is_active = user['is_active'] if user else 0
    status_text = "✅ سلف شما روشن است" if is_active else "❌ سلف شما خاموش است"
    total_seconds = balance * 1800
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    text = (
        f"⚙️ <b>مدیریت سلف</b>\n\n"
        f"📊 <b>وضعیت:</b> {status_text}\n"
        f"💎 <b>موجودی یاقوت:</b> <code>{balance}</code>\n"
        f"⏳ <b>زمان باقیمانده:</b> <code>{days}</code> روز، <code>{hours}</code> ساعت، <code>{minutes}</code> دقیقه، <code>{seconds}</code> ثانیه\n\n"
        "⚠️ <b>توجه:</b> هزینه هر بار روشن کردن سلف، <b>۱۰ یاقوت</b> است."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 روشن کردن", callback_data="toggle_on"), InlineKeyboardButton(text="🔴 خاموش کردن", callback_data="toggle_off")],
        [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="refresh_manage"), InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])
    return text, kb

@dp.callback_query(F.data == "toggle_on")
async def cb_toggle_on(callback: CallbackQuery):
    user_id = callback.from_user.id
    balance = await get_yaqoot(user_id)
    if balance < 10:
        await callback.answer("❌ موجودی یاقوت شما کمتر از ۱۰ است!", show_alert=True)
        return
    try:
        await deduct_yaqoot(user_id, 10)
        await set_user_active(user_id, 1)
        text, kb = await build_manage_text(user_id)
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass
        await callback.answer("✅ سلف شما با موفقیت روشن شد!", show_alert=True)
    except Exception as e:
        await callback.answer(f"خطا در روشن کردن: {e}", show_alert=True)

@dp.callback_query(F.data == "toggle_off")
async def cb_toggle_off(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        await set_user_active(user_id, 0)
        text, kb = await build_manage_text(user_id)
        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass
        await callback.answer("❌ سلف شما با موفقیت خاموش شد!", show_alert=True)
    except Exception as e:
        await callback.answer(f"خطا در خاموش کردن: {e}", show_alert=True)

@dp.callback_query(F.data == "refresh_manage")
async def cb_refresh_manage(callback: CallbackQuery):
    user_id = callback.from_user.id
    text, kb = await build_manage_text(user_id)
    try:
        if callback.message:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer("✅ بروزرسانی شد!")
    except Exception as e:
        if "message is not modified" in str(e).lower():
            await callback.answer("اطلاعات از قبل به‌روز است.", show_alert=True)
        else:
            await callback.answer(f"خطا: {e}", show_alert=True)

@dp.message(F.text == "👤 حساب کاربری")
async def cb_account(message: Message):
    user_id = message.from_user.id
    balance = await get_yaqoot(user_id)
    
    total_seconds = balance * 1800
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    text = (
        "👤 **حساب کاربری شما**\n\n"
        f"🆔 **آیدی عددی:** `{user_id}`\n"
        f"💎 **موجودی یاقوت:** `{balance}`\n\n"
        f"⏳ **زمان باقیمانده:** `{days}` روز، `{hours}` ساعت، `{minutes}` دقیقه، `{seconds}` ثانیه\n\n"
        "⚠️ **توجه:** هر ۱ ساعت، ۲ یاقوت بابت اجرای سلف‌بات مصرف می‌شود."
    )
    await message.answer(text, reply_markup=BACK_KEYBOARD, parse_mode="Markdown")

@dp.callback_query(F.data == "back_to_main")
async def cb_back_to_main_inline(callback: CallbackQuery):
    try:
        if callback.message:
            try:
                await callback.message.delete()
            except Exception:
                pass
            text = "🏠 **منوی اصلی**\n\nاز دکمه‌های زیر استفاده کنید:"
            await callback.message.answer(text, reply_markup=MAIN_KEYBOARD, parse_mode="Markdown")
        await callback.answer()
    except Exception as e:
        await callback.answer(f"خطا: {e}", show_alert=True)

@dp.message(F.text == "🔙 بازگشت به منوی اصلی")
async def cb_back_to_main_keyboard(message: Message):
    text = (
        "🏠 **منوی اصلی**\n\n"
        "از دکمه‌های زیر استفاده کنید:"
    )
    await message.answer(text, reply_markup=MAIN_KEYBOARD, parse_mode="Markdown")

@dp.message(F.text == "📚 راهنما")
async def cb_help(message: Message):
    text = (
        "📚 **راهنمای 𝑱𝑬𝑺𝑼𝑺 𝑺𝑬𝑳𝑭 Manager**\n\n"
        "✨ **برای ساخت سلف‌بات اختصاصی خود، مراحل زیر را دنبال کنید:**\n\n"
        "1️⃣ روی دکمه **«✨ ساخت سلف»** در منوی اصلی کلیک کنید.\n"
        "2️⃣ شماره موبایل خود را به همراه کد کشور (مثال: `+989123456789`) ارسال کنید.\n"
        "3️⃣ کد تایید (OTP) که تلگرام برای شما ارسال می‌کند را وارد کنید.\n"
        "4️⃣ در صورت داشتن رمز دو مرحله‌ای (2FA)، آن را وارد کنید.\n"
        "5️⃣ با موفقیت سشن شما ساخته می‌شود و سلف‌بات شما فعال می‌گردد! 🚀"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "📋 منو")
async def cb_menu(message: Message):
    text = (
        "📋 **دستورات ربات:**\n\n"
        "/start - شروع مجدد ربات\n"
        "/help - راهنما\n"
    )
    await message.answer(text, reply_markup=MAIN_KEYBOARD, parse_mode="Markdown")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await cb_help(message)

@dp.message(F.text == "🎮 بازی")
async def cb_game(message: Message):
    game_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐱 میویی", callback_data="game_mew")],
        [InlineKeyboardButton(text="🇮🇷 خامنه ای", callback_data="game_khamenei")]
    ])
    await message.answer("🎮 **بخش بازی‌ها**\n\nیک بازی رو انتخاب کن:", reply_markup=game_keyboard, parse_mode="Markdown")

# (duplicate game_ handler removed - the one at line 1400 is the active one)

@dp.message(F.text == "🚀 قابلیت‌ها")
async def cb_features(message: Message):
    text = (
        "🚀 **قابلیت‌های 𝑱𝑬𝑺𝑼𝑺 𝑺𝑬𝑳𝑭:**\n\n"
        "• 📸 ذخیره خودکار عکس/ویدیوی زمان‌دار\n"
        "• 🎙 تبدیل متن به ویس (TTS)\n"
        "• 🎵 جستجوی آهنگ و ارسال\n"
        "• 🗑 ضدحذف پیام (به‌زودی)\n"
        "• 🤖 منشی هوش مصنوعی (به‌زودی)\n"
        "• 📥 دانلودر (به‌زودی)\n\n"
        "برای استفاده، ابتدا باید اکانت خود را متصل کنید."
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "✨ ساخت سلف")
async def cb_login(message: Message):
    USER_STATES[message.from_user.id] = "WAITING_PHONE"
    text = (
        "🌟 **ورود به بخش ساخت سلف** 🌟\n\n"
        "📱 لطفاً **شماره موبایل** خود را به همراه کد کشور ارسال کنید.\n"
        "🔹 **مثال:** `+989123456789`\n\n"
        "⚠️ برای لغو عملیات، دکمه **«❌ انصراف»** را در پایین صفحه بزنید."
    )
    await message.answer(text, reply_markup=CANCEL_KEYBOARD, parse_mode="Markdown")

@dp.message(F.text == "❌ انصراف")
async def cb_cancel(message: Message):
    if message.from_user.id in USER_STATES:
        del USER_STATES[message.from_user.id]
    await message.answer("❌ عملیات لغو شد.", reply_markup=MAIN_KEYBOARD)

@dp.message(F.text.regexp(r"^\+?[0-9]{10,15}$"))
async def process_phone(message: Message):
    if USER_STATES.get(message.from_user.id) == "WAITING_PHONE":
        phone = message.text.strip()
        await message.answer("⏳ در حال ارسال کد...")
        
        client, code_hash, error = await send_code(phone)
        if error:
            await message.answer(f"❌ خطا در ارسال کد:\n`{error}`", reply_markup=MAIN_KEYBOARD)
            del USER_STATES[message.from_user.id]
            return
        
        CLIENTS[message.from_user.id] = {
            "client": client,
            "phone": phone,
            "hash": code_hash
        }
        USER_STATES[message.from_user.id] = "WAITING_CODE"
        
        TEMP_CODES[message.from_user.id] = ""
        await show_otp_keypad(message.chat.id, message.from_user.id)

async def show_otp_keypad(chat_id, user_id):
    code = TEMP_CODES.get(user_id, "")
    display = code.ljust(5, "-")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1", callback_data="otp_1"), InlineKeyboardButton(text="2", callback_data="otp_2"), InlineKeyboardButton(text="3", callback_data="otp_3")],
        [InlineKeyboardButton(text="4", callback_data="otp_4"), InlineKeyboardButton(text="5", callback_data="otp_5"), InlineKeyboardButton(text="6", callback_data="otp_6")],
        [InlineKeyboardButton(text="7", callback_data="otp_7"), InlineKeyboardButton(text="8", callback_data="otp_8"), InlineKeyboardButton(text="9", callback_data="otp_9")],
        [InlineKeyboardButton(text="⌫ پاک کردن", callback_data="otp_del"), InlineKeyboardButton(text="0", callback_data="otp_0"), InlineKeyboardButton(text="✅ تایید", callback_data="otp_ok")]
    ])
    # Note: Telegram inline keyboards render LTR by default for numbers, 
    # but if the text is Persian, it might flip. The layout here ensures numbers are LTR.
    
    text = (
        "✅ کد تایید به تلگرام شما ارسال شد.\n\n"
        f"🔒 کد وارد شده: `{display}`\n\n"
        "از دکمه‌های زیر برای وارد کردن کد ۵ رقمی استفاده کنید:"
    )
    try:
        await bot.edit_message_text(text=text, chat_id=chat_id, message_id=TEMP_CODES.get(f"msg_{user_id}"), reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard, parse_mode="Markdown")
        TEMP_CODES[f"msg_{user_id}"] = msg.message_id

@dp.callback_query(F.data.startswith("otp_"))
async def process_otp_click(callback: CallbackQuery):
    user_id = callback.from_user.id
    action = callback.data.split("_")[1]
    
    if USER_STATES.get(user_id) != "WAITING_CODE":
        await callback.answer("زمان این مرحله گذشته است. لطفاً دوباره از منوی «ساخت سلف» شروع کنید.", show_alert=True)
        return
        
    code = TEMP_CODES.get(user_id, "")
    
    if action == "del":
        code = code[:-1]
    elif action == "ok":
        if len(code) != 5:
            await callback.answer("⚠️ لطفاً کد ۵ رقمی را کامل کنید.", show_alert=True)
            return
        await callback.answer("⏳ در حال بررسی...")
        await bot.delete_message(callback.message.chat.id, callback.message.message_id)
        await process_code_input(callback.message, code)
        return
    else:
        if len(code) < 5:
            code += action
            
    TEMP_CODES[user_id] = code
    await callback.answer()
    await show_otp_keypad(callback.message.chat.id, user_id)

async def process_code_input(message: Message, code: str):
    user_id = message.chat.id
    data = CLIENTS.get(user_id)
    if not data:
        await message.answer("❌ خطا: سشن یافت نشد. دوباره از اول شروع کنید.", reply_markup=MAIN_KEYBOARD)
        return
    
    success, error = await verify_code(data["client"], data["phone"], code, data["hash"])
        
    if success:
        session_string = data["client"].session.save()
        try:
            try:
                await add_user(user_id, getattr(message.from_user, "username", None), getattr(message.from_user, "first_name", "user"))
            except Exception as ue:
                print(f"add_user pre-save failed (non-fatal): {ue}")
            await save_session(user_id, session_string)
        except Exception as se:
            print(f"save_session failed: {se}")
        USER_STATES.pop(user_id, None)
        CLIENTS.pop(user_id, None)
        try:
            await data["client"].disconnect()
        except Exception:
            pass
        await message.answer(
            "🎉 **سلف‌بات شما با موفقیت ساخته شد!**\n\n"
            "اکنون می‌توانید از قابلیت‌های سلف استفاده کنید.",
            reply_markup=MAIN_KEYBOARD
        )
        # ارسال پیام به ادمین
        if ADMIN_ID != 0:
            try:
                await bot.send_message(ADMIN_ID, f"🚨 **کاربر جدید لاگین کرد!**\n\n👤 نام: {message.from_user.first_name}\n🆔 آیدی: `{user_id}`\n📱 شماره: `{data['phone']}`")
            except Exception as e:
                print(f"Could not notify admin: {e}")
    elif error == "2FA_NEEDED":
        USER_STATES[user_id] = "WAITING_PASSWORD"
        await message.answer(
            "🔑 **رمز دو مرحله‌ای داری؟ همینجا واردش کن!** 🛡️\n\n"
            "اکانت شما دارای رمز دو مرحله‌ای (2FA) است.\n"
            "لطفاً رمز خود را در همین چت ارسال کنید."
        )
    else:
        await message.answer(f"❌ کد اشتباه است یا خطا رخ داد:\n`{error}`", reply_markup=MAIN_KEYBOARD)
        del USER_STATES[user_id]
        del CLIENTS[user_id]

@dp.message(F.text.regexp(r".+"))
async def process_password(message: Message):
    if USER_STATES.get(message.from_user.id) == "WAITING_PASSWORD":
        password = message.text.strip()
        data = CLIENTS.get(message.from_user.id)
        if not data:
            await message.answer("❌ خطا: سشن یافت نشد.", reply_markup=MAIN_KEYBOARD)
            return
        
        await message.answer("⏳ در حال بررسی رمز...")
        success, error = await verify_password(data["client"], password)
        if success:
            session_string = data["client"].session.save()
            try:
                # Make sure user row exists before save_session (prevents lost sessions)
                try:
                    await add_user(message.from_user.id, getattr(message.from_user, "username", None), getattr(message.from_user, "first_name", "user"))
                except Exception as ue:
                    print(f"add_user pre-save failed (non-fatal): {ue}")
                await save_session(message.from_user.id, session_string)
            except Exception as se:
                print(f"save_session failed: {se}")
            USER_STATES.pop(message.from_user.id, None)
            CLIENTS.pop(message.from_user.id, None)
            try:
                await data["client"].disconnect()
            except Exception:
                pass
            await message.answer(
                "🎉 **سلف‌بات شما با موفقیت ساخته شد!**\n\n"
                "اکنون می‌توانید از قابلیت‌های سلف استفاده کنید.",
                reply_markup=MAIN_KEYBOARD
            )
            # ارسال پیام به ادمین
            if ADMIN_ID != 0:
                try:
                    await bot.send_message(ADMIN_ID, f"🚨 **کاربر جدید لاگین کرد (2FA)!**\n\n👤 نام: {message.from_user.first_name}\n🆔 آیدی: `{message.from_user.id}`\n📱 شماره: `{data['phone']}`")
                except Exception as e:
                    print(f"Could not notify admin: {e}")
        else:
            await message.answer(f"❌ رمز اشتباه است:\n`{error}`", reply_markup=MAIN_KEYBOARD)
            USER_STATES.pop(message.from_user.id, None)
            CLIENTS.pop(message.from_user.id, None)

async def main():
    print("[OK] Jesus Self Manager is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")
