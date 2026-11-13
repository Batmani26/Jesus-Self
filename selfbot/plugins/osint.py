"""OSINT plugin: Stalk & Security module. Sends user input to a target bot and forwards the response."""
import asyncio
from telethon import events
from selfbot.config import config

# نام ربات هدف رو اینجا تنظیم کن (مثلا @TargetBot)
TARGET_BOT = "@funstatloper_bot"

USER_STATES = {}

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}استاک$"))
    async def osint_cmd(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        USER_STATES[me.id] = "WAITING_TARGET"
        await event.delete()
        await client.send_message("me", 
            "🛡 **بخش استاک و امنیت**\n\n"
            "لطفاً **آیدی عددی** یا **یوزرنیم** مورد نظر را ارسال کنید:\n"
            "(برای انصراف .انصراف را بزنید)"
        )

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}انصراف$"))
    async def cancel_cmd(event: events.NewMessage.Event) -> None:
        me = await client.get_me()
        if me.id in USER_STATES:
            del USER_STATES[me.id]
        await event.edit("❌ عملیات لغو شد.")

    @client.on(events.NewMessage(outgoing=True, pattern=r"^(?!\.).+"))
    async def process_target(event: events.NewMessage.Event):
        me = await client.get_me()
        if USER_STATES.get(me.id) == "WAITING_TARGET":
            target = event.text.strip()
            del USER_STATES[me.id]
            await event.edit(f"⏳ در حال استعلام `{target}` از ربات امنیتی...")
            
            try:
                # ارسال به ربات هدف
                from selfbot.manager import OSINT_QUEUE
                await OSINT_QUEUE.put({"target": target, "user_id": me.id})
                await event.edit("⏳ درخواست شما در صف بررسی قرار گرفت. نتیجه به زودی در سیو مسیج ارسال می‌شود.")
            except Exception as e:
                await event.edit(f"❌ خطا در استعلام: `{e}`")
