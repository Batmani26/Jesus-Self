"""Currency plugin: `.دلار` fetches live dollar price from Nobitex."""
import aiohttp
from telethon import events
from selfbot.config import config

import re

async def get_live_prices():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    text = "💵 **قیمت‌های لحظه‌ای بازار:**\n\n"
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            # 1. Fetch all prices from a reliable public API
            async with session.get("https://api.tgju.org/v1/market/indicator/summary-table-data", timeout=15) as resp:
                if resp.status == 200:
                    # Using TGJU's public data (sometimes works with simple headers)
                    pass
                    
            # Using Navasan (a reliable free API)
            async with session.get("https://api.navasan.ir/v1/market/price", timeout=15) as resp2:
                if resp2.status == 200:
                    data = await resp2.json()
                    usd = data.get('usd', {}).get('value', 0)
                    eur = data.get('eur', {}).get('value', 0)
                    gold18 = data.get('gold18', {}).get('value', 0)
                    emami = data.get('sekke', {}).get('value', 0)
                    
                    text += f"🇺🇸 دلار: {usd:,} تومان\n"
                    text += f"🇪🇺 یورو: {eur:,} تومان\n"
                    text += f"🥇 طلا ۱۸ عیار: {gold18:,} تومان\n"
                    text += f"🪙 سکه امامی: {emami:,} تومان\n"
                    text += "\n📊 منبع: نوسان"
                    return text
    except Exception as e:
        print(f"Currency API error: {e}")
        
    # Fallback to Nobitex for Dollar
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get("https://api.nobitex.ir/v2/orderbook/USDTIRT", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    last_trade = data.get('lastTradePrice', 0)
                    dollar_toman = int(float(last_trade) / 10)
                    return f"💵 **قیمت‌های لحظه‌ای بازار:**\n\n🇺🇸 دلار (تتر): {dollar_toman:,} تومان\n\n📊 منبع: نوبیتکس (سایر قیمت‌ها در دسترس نیست)"
    except:
        pass
        
    return "❌ خطا در دریافت قیمت‌ها."

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}(قیمت ارز|دلار|قیمت دلار)$"))
    async def dollar_cmd(event: events.NewMessage.Event) -> None:
        await event.edit("⏳ در حال دریافت قیمت‌های لحظه‌ای...")
        price_text = await get_live_prices()
        await event.edit(price_text)
