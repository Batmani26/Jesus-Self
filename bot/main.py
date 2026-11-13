"""ربات مدیریت (Management Bot) - Jesus Self"""
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, ForceReply, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import F
from bot.database import add_user, get_user, set_user_phone, save_session, get_yaqoot, add_yaqoot, get_all_active_users, deduct_yaqoot, deactivate_user
from bot.login import send_code, verify_code, verify_password

BOT_TOKEN = "9117892584:AAHF4j8MgWhJdXCmXIGBQfJk2OMVnQjWNhs"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# آیدی عددی ادمین (خودت) رو اینجا بذار تا پیام لاگین رو برات بفرسته
# برای پیدا کردن آیدی خودت میتونی از ربات @userinfobot استفاده کنی
ADMIN_ID = 7099566033

USER_STATES = {}
CLIENTS = {}
TEMP_CODES = {}

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✨ ساخت سلف"), KeyboardButton(text="👤 حساب کاربری")],
        [KeyboardButton(text="📚 راهنما")]
    ],
    resize_keyboard=True
)

CANCEL_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ انصراف")]],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: Message):
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

@dp.message(F.text == "👤 حساب کاربری")
async def cb_account(message: Message):
    user_id = message.from_user.id
    balance = await get_yaqoot(user_id)
    
    remaining_hours = balance // 2
    remaining_days = remaining_hours // 24
    
    text = (
        "👤 **حساب کاربری شما**\n\n"
        f"🆔 **آیدی عددی:** `{user_id}`\n"
        f"💎 **موجودی یاقوت:** `{balance}`\n\n"
        f"⏳ **زمان باقیمانده:**\n"
        f"🕒 **{remaining_hours}** ساعت\n"
        f"📅 **{remaining_days}** روز\n\n"
        "⚠️ **توجه:** هر ۱ ساعت، ۲ یاقوت بابت اجرای سلف‌بات مصرف می‌شود."
    )
    await message.answer(text, parse_mode="Markdown")

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
        await callback.answer("زمان این مرحله گذشته است.")
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
