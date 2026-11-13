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
                async with client.conversation(TARGET_BOT, timeout=30) as conv:
                    await conv.send_message(f"{target}")
                    
                    # Wait for the final response (skip loading messages)
                    while True:
                        response = await conv.get_response()
                        if "Looking for data" in response.text or "Lοокinց" in response.text or "Loading" in response.text:
                            continue
                        break
                    
                # ارسال پاسخ به سیو مسیج
                await client.send_message("me", f"🔍 **نتیجه استعلام `{target}`:**\n\n{response.text}\n\n✨ **Jesus Self** ✨")
                await event.delete()
            except asyncio.TimeoutError:
                await event.edit("❌ ربات امنیتی پاسخی نداد (Timeout).")
            except Exception as e:
                await event.edit(f"❌ خطا در استعلام: `{e}`")
