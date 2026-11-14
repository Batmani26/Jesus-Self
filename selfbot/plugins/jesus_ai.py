"""Jesus AI plugin: `.جیزس <text>` chats with an AI assistant."""
import aiohttp
import os
import json
from telethon import events
from selfbot.config import config

# API Keys from environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

async def get_groq_response(prompt: str) -> str:
    if not GROQ_API_KEY:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=15) as resp:
                if resp.status == 200:
                    res_json = await resp.json()
                    return res_json['choices'][0]['message']['content']
    except Exception:
        pass
    return None

async def get_gemini_response(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=15) as resp:
                if resp.status == 200:
                    res_json = await resp.json()
                    return res_json['candidates'][0]['content']['parts'][0]['text']
    except Exception:
        pass
    return None

async def get_ai_response(prompt: str) -> str:
    # Try Groq first (fastest)
    res = await get_groq_response(prompt)
    if res:
        return res
        
    # Fallback to Gemini
    res = await get_gemini_response(prompt)
    if res:
        return res
        
    # Ultimate fallback to Pollinations (no key needed)
    url = "https://text.pollinations.ai/" + prompt
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    return await response.text()
    except Exception:
        pass
        
    return "❌ متاسفانه در حال حاضر هیچ‌کدوم از سرویس‌های هوش مصنوعی پاسخ ندادن."

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
