from telethon import events
from telethon.tl.custom import Button
from selfbot.config import config
import re
from bot.database import get_yaqoot, get_meow_target_db

def _b(t, d):
    return Button.inline(t, d.encode())






async def _main_menu(event, balance):
    kb = [
        [_b("میویی", "cat_meowie_info")],
        [_b("بازی ها", "cat_games"), _b("ابزار ها", "cat_tools")],
        [_b("نظارت و سرگرمی", "cat_fun"), _b("تقلب", "cat_cheat")],
        [_b("استاک و امنیت", "cat_security")],
        [_b("بروزرسانی", "refresh_panel"), _b("بستن پنل", "feat_close")],
    ]
    text = f"پنل مدیریت\n\n💰 موجودی یاقوت: **{balance}**"
    target = event.message if hasattr(event, "message") and event.message else event
    await target.respond(text, buttons=kb, parse_mode="md")


async def _meowie_menu(event):
    kb = [
        [_b("میو روشن", "meow_on"), _b("میو خاموش", "meow_off")],
        [_b("نجات پیشی روشن", "savecat_on"), _b("نجات پیشی خاموش", "savecat_off")],
        [_b("ماهیگیری روشن", "fishing_on"), _b("ماهیگیری خاموش", "fishing_off")],
        [_b("بازگشت", "refresh_panel")],
    ]
    target = event.message if hasattr(event, "message") and event.message else event
    target = event.message if hasattr(event, "message") and event.message else event
    await target.respond("بخش میویی", buttons=kb)

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern="^" + re.escape(p) + "پنل$"))
    async def panel_cmd(event: events.NewMessage.Event) -> None:
        me = await event.client.get_me()
        try:
            balance = await get_yaqoot(me.id)
        except Exception:
            balance = 0
        if balance <= 0:
            await event.reply("موجودی یاقوت شما به پایان رسیده است. ابتدا شارژ کنید.")
            return
        await _main_menu(event, balance)

    @client.on(events.CallbackQuery())
    async def panel_callback(event: events.CallbackQuery.Event) -> None:
        data = event.data.decode(chr(39)+chr(117)+chr(116)+chr(102)+chr(45)+chr(56)+chr(39))
        me = await event.client.get_me()
        try:
            balance = await get_yaqoot(me.id)
        except Exception:
            balance = 0
        if data == "feat_close":
            await event.delete()
        elif data == "refresh_panel":
            try:
                await event.delete()
            except Exception:
                pass
            await _main_menu(event.message, balance)
        elif data == "cat_meowie_info":
            await _meowie_menu(event)
        elif data in ("cat_games","cat_tools","cat_fun","cat_cheat","cat_security"):
            await event.answer("به زودی", alert=True)
        elif data == "meow_on":
            await event.answer("برای فعال‌سازی دستور .میو روشن را بزن", alert=True)
        elif data == "meow_off":
            await event.answer("برای خاموش‌کردن دستور .میو خاموش را بزن", alert=True)
        elif data == "savecat_on":
            await event.answer("برای فعال‌سازی دستور .نجات پیشی روشن را بزن", alert=True)
        elif data == "savecat_off":
            await event.answer("برای خاموش‌کردن دستور .نجات پیشی خاموش را بزن", alert=True)
        elif data == "fishing_on":
            await event.answer("برای فعال‌سازی دستور .ماهیگیری روشن را بزن", alert=True)
        elif data == "fishing_off":
            await event.answer("برای خاموش‌کردن دستور .ماهیگیری خاموش را بزن", alert=True)
