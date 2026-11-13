"""Panel plugin: `.پنل` opens an inline menu of features."""
from telethon import events
from telethon.tl.custom import Button

from selfbot.config import config

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}پنل"))
    async def panel_cmd(event: events.NewMessage.Event) -> None:
        try:
            results = await client.inline_query('SelfJesusBot', 'panel')
            await results[0].click(event.chat_id, reply_to_msg_id=event.reply_to_msg_id)
            await event.delete()
        except Exception as e:
            await event.edit(f"❌ خطا در باز کردن پنل: {e}")

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
