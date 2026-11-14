"""Currency plugin: `.دلار` fetches live dollar price from Nobitex."""
import aiohttp
from telethon import events
from selfbot.config import config

import re

async def get_live_prices():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    text = "💵 **قیمت‌های لحظه‌ای بازار:**\n\n"
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            # 1. Fetch Dollar from Nobitex (very reliable)
            async with session.get("https://api.nobitex.ir/v2/orderbook/USDTIRT", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    last_trade = data.get('lastTradePrice', 0)
                    dollar_toman = int(float(last_trade) / 10)
                    text += f"🇺🇸 دلار: {dollar_toman:,} تومان\n"

            # 2. Fetch Gold from TGJU (scraping)
            async with session.get("https://www.tgju.org/profile/geram18", timeout=10) as resp2:
                if resp2.status == 200:
                    html = await resp2.text()
                    # Extract price using regex
                    match = re.search(r'<span data-col="info.last_trade.PDrCotVal">([\d,\.]+)</span>', html)
                    if match:
                        gold_price = match.group(1)
                        text += f"🥇 طلا ۱۸ عیار: {gold_price} تومان\n"
                    else:
                        text += "🥇 طلا: نامشخص\n"
            
            # 3. Fetch Euro from TGJU
            async with session.get("https://www.tgju.org/profile/price_eur", timeout=10) as resp3:
                if resp3.status == 200:
                    html = await resp3.text()
                    match = re.search(r'<span data-col="info.last_trade.PDrCotVal">([\d,\.]+)</span>', html)
                    if match:
                        euro_price = match.group(1)
                        text += f"🇪🇺 یورو: {euro_price} تومان\n"
            
            text += "\n📊 منبع: نوبیتکس و TGJU"
            return text
    except Exception as e:
        print(f"Currency error: {e}")
        
    # Fallback to just Nobitex if TGJU fails
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get("https://api.nobitex.ir/v2/orderbook/USDTIRT", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    last_trade = data.get('lastTradePrice', 0)
                    dollar_toman = int(float(last_trade) / 10)
                    return f"💵 **قیمت‌های لحظه‌ای بازار:**\n\n🇺🇸 دلار (تتر): {dollar_toman:,} تومان\n\n📊 منبع: نوبیتکس"
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
