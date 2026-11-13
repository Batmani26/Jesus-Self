"""Panel plugin: `.پنل` opens an inline menu of features."""
from telethon import events
from telethon.tl.custom import Button

from selfbot.config import config

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}پنل"))
    async def panel_cmd(event: events.NewMessage.Event) -> None:
        print(f"[DEBUG] Panel command matched in chat: {event.chat_id}")
        buttons = [
            [Button.inline("🎮 بازی ها", data=b"cat_games")],
            [Button.inline("🛠 ابزار ها", data=b"cat_tools")],
            [Button.inline("👁 نظارت و سرگرمی", data=b"cat_fun")],
            [Button.inline("🎭 تقلب", data=b"cat_cheat")],
            [Button.inline("🛡 استاک و امنیت", data=b"cat_security")],
            [Button.inline("❌ بستن پنل", data=b"feat_close")]
        ]
        text = (
            "🤖 <b>پنل کنترل 𝑱𝑬𝑺𝑼𝑺 𝑺𝑬𝑳𝑭</b>\n\n"
            "از منوی زیر یک قابلیت را انتخاب کنید:"
        )
        # Use send_message with parse_mode='html' to ensure buttons render
        await event.client.send_message(event.chat_id, text, buttons=buttons, parse_mode='html')
        await event.delete()

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
