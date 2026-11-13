"""ربات مدیریت (Management Bot) - Jesus Self"""
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
import hashlib
import datetime
import pytz
from datetime import datetime
from persiantools.jdatetime import JalaliDateTime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram import F
from bot.database import add_user, get_user, set_user_phone, save_session, get_yaqoot, add_yaqoot, get_all_active_users, deduct_yaqoot, deactivate_user, set_user_active
from bot.login import send_code, verify_code, verify_password

BOT_TOKEN = "9117892584:AAHF4j8MgWhJdXCmXIGBQfJk2OMVnQjWNhs"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# آیدی عددی ادمین (خودت) رو اینجا بذار تا پیام لاگین رو برات بفرسته
# برای پیدا کردن آیدی خودت میتونی از ربات @userinfobot استفاده کنی
ADMIN_ID = 7099566033
MAINTENANCE_MODE = True

USER_STATES = {}
CLIENTS = {}
TEMP_CODES = {}
ACTIVE_PANELS = {} # {(chat_id, message_id): user_id}

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
        date_shamsi = JalaliDateTime(now_tehran.year, now_tehran.month, now_tehran.day).strftime("%Y/%m/%d")
        
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
            [InlineKeyboardButton(text="👀 نظارت و سرگرمی", callback_data="cat_fun"), InlineKeyboardButton(text="🎭 تقلب", callback_data="cat_cheat")],
            [InlineKeyboardButton(text="🛡 استاک و امنیت", callback_data="cat_security"), InlineKeyboardButton(text="❌ بستن پنل", callback_data="feat_close")],
            [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="refresh_panel")]
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
        date_shamsi = JalaliDateTime(now_tehran.year, now_tehran.month, now_tehran.day).strftime("%Y/%m/%d")
        
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
                await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text)
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
    date_shamsi = JalaliDateTime(now_tehran.year, now_tehran.month, now_tehran.day).strftime("%Y/%m/%d")
    
    text = (
        "🤖 **پنل کنترل 𝑱𝑬𝑺𝑼𝑺 𝑺𝑬𝑳𝑭**\n\n"
        f"💎 موجودی: **{balance}** یاقوت\n"
        f"⏳ معادل: **{days}** روز، **{hours}** ساعت، **{minutes}** دقیقه، **{seconds}** ثانیه\n"
        f"⏰ ساعت: `{time_str}`\n"
        f"📅 تاریخ شمسی: `{date_shamsi}` | میلادی: `{date_miladi}`\n\n"
        "✨ لطفاً یک قابلیت را از منوی زیر انتخاب کنید:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=callback.message.reply_markup, parse_mode="Markdown")
        await callback.answer("✅ پنل بروزرسانی شد!")
    except Exception:
        await callback.answer("❌ خطا در بروزرسانی.", show_alert=True)

@dp.callback_query(F.data.startswith("cat_"))
async def process_inline_panel_callback(callback: CallbackQuery):
    cat = callback.data.split("_")[1]
    if cat == "games":
        await callback.answer("🎮 بخش بازی‌ها (به‌زودی)", show_alert=True)
    elif cat == "tools":
        await callback.answer("🛠 بخش ابزارها (به‌زودی)", show_alert=True)
    elif cat == "fun":
        await callback.answer("👁 بخش نظارت و سرگرمی (به‌زودی)", show_alert=True)
    elif cat == "cheat":
        await callback.answer("🎭 بخش تقلب (به‌زودی)", show_alert=True)
    elif cat == "security":
        guide_text = (
            "🛡 <b>بخش استاک و امنیت</b>\n\n"
            "<blockquote>سلف ما قابلیتی برای کاربران هموار ساخته که با استفاده از آیدی عددی و یا یوزرنیم شخص، اطلاعاتی از اکانت مورد نظر را به شما نشان دهد.</blockquote>\n\n"
            "<blockquote>جهت استفاده از این قابلیت، شما با ارسال .استاک یک پیامی در سیو مسیج خود دریافت می‌کنید که منتظر دریافت آیدی عددی و یا یوزرنیم از طرف شما است و شما با ارسال آن، اطلاعاتی را در همان سیو مسیج دریافت می‌کنید.</blockquote>\n\n"
            "👇 برای کپی کردن دستور، روی آن کلیک کنید:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 کپی دستور .استاک", callback_data="copy_stalk")],
            [InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="back_to_panel")]
        ])
        try:
            if callback.message:
                await callback.message.edit_text(guide_text, reply_markup=kb, parse_mode="HTML")
            else:
                await callback.bot.edit_message_text(inline_message_id=callback.inline_message_id, text=guide_text, reply_markup=kb, parse_mode="HTML")
            await callback.answer()
        except Exception as e:
            await callback.answer(f"خطا: {e}", show_alert=True)

@dp.callback_query(F.data == "copy_stalk")
async def cb_copy_stalk(callback: CallbackQuery):
    await callback.answer("دستور .استاک کپی شد! (می‌توانید آن را در هر چتی بفرستید)", show_alert=True)

@dp.callback_query(F.data == "back_to_panel")
async def cb_back_to_panel(callback: CallbackQuery):
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
    date_shamsi = JalaliDateTime(now_tehran.year, now_tehran.month, now_tehran.day).strftime("%Y/%m/%d")
    
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
        [InlineKeyboardButton(text="👀 نظارت و سرگرمی", callback_data="cat_fun"), InlineKeyboardButton(text="🎭 تقلب", callback_data="cat_cheat")],
        [InlineKeyboardButton(text="🛡 استاک و امنیت", callback_data="cat_security"), InlineKeyboardButton(text="❌ بستن پنل", callback_data="feat_close")],
        [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="refresh_panel")]
    ])
    try:
        if callback.message:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        else:
            await callback.bot.edit_message_text(inline_message_id=callback.inline_message_id, text=text, reply_markup=kb, parse_mode="Markdown")
        await callback.answer()
    except Exception as e:
        await callback.answer(f"خطا: {e}", show_alert=True)

@dp.callback_query(F.data == "feat_close")
async def close_inline_panel(callback: CallbackQuery):
    await callback.message.delete()

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
    photo_url = "https://i.ibb.co/JwLFZy9c/Jesus-Self-Neon-Telegram-Fantasy-Poster.png"
    
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
    await message.answer(text, reply_markup=BACK_KEYBOARD, parse_mode="HTML")
    await message.answer("👇 برای مدیریت از دکمه‌های شیشه‌ای بالا استفاده کنید.", reply_markup=kb)

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
        [InlineKeyboardButton(text="✅ روشن کردن", callback_data="toggle_on"), InlineKeyboardButton(text="❌ خاموش کردن", callback_data="toggle_off")],
        [InlineKeyboardButton(text="🔄 بروزرسانی", callback_data="refresh_manage")]
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
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer("✅ سلف شما با موفقیت روشن شد!", show_alert=True)
    except Exception as e:
        await callback.answer(f"خطا در روشن کردن: {e}", show_alert=True)
        await callback.message.answer(f"خطای دقیق: `{e}`", parse_mode="Markdown")

@dp.callback_query(F.data == "toggle_off")
async def cb_toggle_off(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        await set_user_active(user_id, 0)
        text, kb = await build_manage_text(user_id)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer("❌ سلف شما با موفقیت خاموش شد!", show_alert=True)
    except Exception as e:
        await callback.answer(f"خطا در خاموش کردن: {e}", show_alert=True)
        await callback.message.answer(f"خطای دقیق: `{e}`", parse_mode="Markdown")

@dp.callback_query(F.data == "refresh_manage")
async def cb_refresh_manage(callback: CallbackQuery):
    user_id = callback.from_user.id
    text, kb = await build_manage_text(user_id)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer("✅ بروزرسانی شد!")

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
        "📚 **راهنمای 𝑱𝑬𝑺𝑼𝑺 𝑺𝑬𝑳𝑭 Manager:**\n\n"
        "این ربات به شما امکان می‌دهد یک سلف‌بات بسازید.\n\n"
        "**مراحل:**\n"
        "1️⃣ روی دکمه «🚀 ساخت سلف» کلیک کنید.\n"
        "2️⃣ شماره موبایل را با فرمت +98... وارد کنید.\n"
        "3️⃣ کد تایید (OTP) را وارد کنید.\n"
        "4️⃣ اگر رمز دو مرحله‌ای دارید، وارد کنید.\n"
        "5️⃣ سشن ساخته می‌شود!\n\n"
        "⚠️ **هشدار:** سلف‌بات با اکانت شخصی شما کار می‌کند."
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

@dp.callback_query(F.data.startswith("game_"))
async def process_game(callback: CallbackQuery):
    game_type = callback.data.split("_")[1]
    if game_type == "mew":
        await callback.message.answer("🐱 بخش های متفاوت میویی را میتوانید با دستور .پنل کنترل کنید")
    elif game_type == "khamenei":
        await callback.message.answer("🇮🇷 رهبر انقلاب، حضرت آیت‌الله خامنه‌ای.")
    await callback.answer()

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
        await save_session(user_id, session_string)
        del USER_STATES[user_id]
        del CLIENTS[user_id]
        await data["client"].disconnect()
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
            await save_session(message.from_user.id, session_string)
            del USER_STATES[message.from_user.id]
            del CLIENTS[message.from_user.id]
            await data["client"].disconnect()
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
            del USER_STATES[message.from_user.id]
            del CLIENTS[message.from_user.id]

async def main():
    print("[OK] Jesus Self Manager is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")
