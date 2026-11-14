"""Jesus AI plugin: `.جیزس <text>` chats with an AI assistant."""
import aiohttp
from telethon import events
from selfbot.config import config

async def get_ai_response(prompt: str) -> str:
    url = "https://text.pollinations.ai/" + prompt
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    return await response.text()
                return "❌ متاسفانه در حال حاضر نمی‌تونم پاسخ بدم."
    except Exception as e:
        return f"❌ خطا در ارتباط با هوش مصنوعی: `{e}`"

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}جیزس (.+)$"))
    async def jesus_ai(event: events.NewMessage.Event) -> None:
        prompt = event.pattern_match.group(1).strip()
        await event.edit("⏳ در حال فکر کردن...")
        
        response = await get_ai_response(prompt)
        
        # Split response if it's too long
        if len(response) > 4000:
            response = response[:4000] + "..."
            
        await event.edit(f"🤖 **جیزس:**\n\n{response}")
