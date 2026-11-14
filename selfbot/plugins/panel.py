"""Panel plugin: `.پنل` opens an inline menu of features."""
from telethon import events
from telethon.tl.custom import Button

from selfbot.config import config
from bot.database import get_yaqoot

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}پنل$"))
    async def panel_cmd(event: events.NewMessage.Event) -> None:
        me = await event.client.get_me()
        try:
            balance = await get_yaqoot(me.id)
        except Exception:
            balance = 0
        if balance <= 0:
            await event.reply("❌ **موجودی یاقوت شما به پایان رسیده است** — ابتدا شارژ کنید", parse_mode="md")
            return
        buttons = [
            [Button.inline("وضعیت سلف‌بات", b"feat_status"), Button.inline("ذخیره‌ساز", b"feat_saver")],
            [Button.inline("ویس", b"feat_voice"), Button.inline("موزیک", b"feat_music")],
            [Button.inline("بستن پنل", b"feat_close")],
        ]
        text = f"🎛 **پنل مدیریت**\n\n💰 موجودی یاقوت: **{balance}**\n\nیک گزینه را انتخاب کنید:"
        await event.reply(text, buttons=buttons, parse_mode="md")

    @client.on(events.CallbackQuery())
    async def panel_callback(event: events.CallbackQuery.Event) -> None:
        data = event.data.decode('utf-8')
        try:
            if data == "feat_close":
                await event.delete()
            elif data == "feat_status":
                await event.answer("✅ سلف‌بات آنلاین است.", alert=True)
            elif data == "feat_saver":
                await event.answer("📸 قابلیت ذخیره زمان‌دار فعال است. فقط کافیه کسی برات عکس زمان‌دار بفرسته.", alert=True)
            elif data == "feat_voice":
                await event.answer("🎙 برای تبدیل متن به ویس از دستور .say <text> استفاده کن.", alert=True)
            elif data == "feat_music":
                await event.answer("🎵 برای جستجوی آهنگ از دستور .song <name> استفاده کن.", alert=True)
            elif data == "cat_games":
                await event.answer("🎮 بخش بازی‌ها (به‌زودی)", alert=True)
            elif data == "cat_tools":
                await event.answer("🛠 بخش ابزارها (به‌زودی)", alert=True)
            elif data == "cat_fun":
                await event.answer("👁 بخش نظارت و سرگرمی (به‌زودی)", alert=True)
            elif data == "cat_cheat":
                await event.answer("🎭 بخش تقلب (به‌زودی)", alert=True)
            elif data == "cat_security":
                await event.answer("🛡 بخش استاک و امنیت (به‌زودی)", alert=True)
        except Exception:
            pass
