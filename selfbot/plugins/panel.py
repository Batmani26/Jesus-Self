"""Panel plugin: `.پنل` opens an inline menu of features."""
from telethon import events
from telethon.tl.custom import Button

from selfbot.config import config

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}پنل"))
    async def panel_cmd(event: events.NewMessage.Event) -> None:
        # سلف‌بات‌ها نمی‌توانند دکمه شیشه‌ای بفرستند. لینک به ربات مدیریت می‌دهیم.
        text = (
            "🤖 **پنل کنترل 𝑱𝑬𝑺𝑼𝑺 𝑺𝑬𝑳𝑭**\n\n"
            "برای دسترسی به منوی شیشه‌ای و مدیریت قابلیت‌ها، لطفاً به ربات مدیریت مراجعه کنید:\n\n"
            "👉 [کلیک کنید: @SelfJesusBot](https://t.me/SelfJesusBot)"
        )
        await event.edit(text, parse_mode="md", link_preview=False)

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
