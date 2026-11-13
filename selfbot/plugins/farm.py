"""Farm plugin: `.فارم تاس <1-6>` rolls dice until the desired number and sends it."""
import asyncio
from telethon import events
from telethon.tl.types import InputMediaDice
from selfbot.config import config

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}فارم تاس ([1-6])$"))
    async def farm_dice(event: events.NewMessage.Event) -> None:
        desired = int(event.pattern_match.group(1))
        await event.edit(f"⏳ در حال فارم کردن تاس {desired}...")
        
        for _ in range(300):
            msg = await client.send_message("me", file=InputMediaDice("🎲"))
            if msg and msg.media and hasattr(msg.media, 'value'):
                if msg.media.value == desired:
                    # Found it! Send the success message to the user
                    await event.edit(
                        f"✅ **تاس {desired} پیدا شد!**\n\n"
                        f"پیام تاس برات توی سیو مسیج ارسال شد.\n"
                        f"فقط کافیه اون پیام رو **فوروارد** کنی به گروه مورد نظر.\n\n"
                        f"⚠️ **توجه:** اگه ربات میویی فرستنده رو چک کنه، ممکنه قبول نکنه."
                    )
                    return
            asyncio.create_task(msg.delete())
            
        await event.edit("❌ متاسفانه تاس مورد نظر پیدا نشد. لطفاً دوباره تلاش کنید.")
