"""Panel plugin: `.پنل` opens an inline menu of features."""
from telethon import events
from telethon.tl.custom import Button

from selfbot.config import config

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}پنل$"))
    async def panel_cmd(event: events.NewMessage.Event) -> None:
        buttons = [
            [Button.inline("📸 ذخیره زمان‌دار", data=b"feat_saver"), Button.inline("🎙 تبدیل به ویس", data=b"feat_voice")],
            [Button.inline("🎵 جستجوی آهنگ", data=b"feat_music"), Button.inline("📊 وضعیت", data=b"feat_status")],
            [Button.inline("❌ بستن پنل", data=b"feat_close")]
        ]
        text = (
            "🤖 **پنل کنترل Jesse Self**\n\n"
            "از منوی زیر یک قابلیت را انتخاب کنید:"
        )
        await event.edit(text, buttons=buttons, parse_mode="md")

    @client.on(events.CallbackQuery())
    async def panel_callback(event: events.CallbackQuery.Event) -> None:
        data = event.data.decode('utf-8')
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
