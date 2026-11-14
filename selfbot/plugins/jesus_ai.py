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
    # Updated to the correct endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=20) as resp:
                if resp.status == 200:
                    res_json = await resp.json()
                    return res_json['candidates'][0]['content']['parts'][0]['text']
                else:
                    print(f"Gemini Error: {resp.status} - {await resp.text()}")
    except Exception as e:
        print(f"Gemini Exception: {e}")
    return None

async def get_ai_response(prompt: str) -> str:
    # We enforce a system prompt to make the AI answer better in Persian
    system_prompt = "You are a helpful, accurate, and up-to-date AI assistant. Answer concisely in Persian. If you don't know the exact current price (like dollar rates), clearly state that you don't have live access to the market, but provide the most recent known information without making up fake numbers."
    full_prompt = f"{system_prompt}\n\nUser: {prompt}"

    # Try Gemini first (better quality for Persian)
    res = await get_gemini_response(full_prompt)
    if res:
        return res
        
    # Fallback to Groq
    res = await get_groq_response(full_prompt)
    if res:
        return res
        
    # Fallback to Pollinations (simpler prompt to avoid rate limits)
    url = f"https://text.pollinations.ai/{prompt}?model=openai"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"Pollinations Error: {response.status}")
    except Exception as e:
        print(f"Pollinations Exception: {e}")
        
    # Ultimate fallback to a generic message
    return "❌ متاسفانه در حال حاضر سرویس‌های هوش مصنوعی پاسخ ندادن. (ممکنه به خاطر محدودیت درخواست باشه، لطفاً چند دقیقه دیگه امتحان کن)"

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}جیزس (.+)$"))
    async def jesus_ai(event: events.NewMessage.Event) -> None:
        prompt = event.pattern_match.group(1).strip()
        
        # Check if the user is asking about the current chat
        context_keywords = ["گپ", "چت", "اینجا", "این گروه", "این چت"]
        is_chat_question = any(k in prompt for k in context_keywords)
        
        context_text = ""
        if is_chat_question:
            messages = await client.get_messages(event.chat_id, limit=10)
            context_lines = []
            for m in reversed(messages):
                if m.text:
                    sender = await m.get_sender()
                    name = getattr(sender, 'first_name', 'Unknown')
                    context_lines.append(f"{name}: {m.text}")
            context_text = "\nContext of recent messages in this chat:\n" + "\n".join(context_lines)
            
        full_prompt = f"User Question: {prompt}{context_text}"
        
        # Send a new message for the thinking status
        status_msg = await event.reply("⏳ در حال فکر کردن...")
        
        response = await get_ai_response(full_prompt)
        
        # Split response if it's too long
        if len(response) > 4000:
            response = response[:4000] + "..."
            
        # Edit the status message with the final answer
        await status_msg.edit(f"🤖 **جیزس:**\n\n{response}")
