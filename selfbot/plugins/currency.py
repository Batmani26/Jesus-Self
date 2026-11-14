"""Currency plugin: `.دلار` fetches live dollar price from Nobitex."""
import aiohttp
from telethon import events
from selfbot.config import config

async def get_live_prices():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    text = "💵 **قیمت‌های لحظه‌ای بازار:**\n\n"
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            # 1. Fetch Dollar from Nobitex
            async with session.get("https://api.nobitex.ir/v2/orderbook/USDTIRT", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    last_trade = data.get('lastTradePrice', 0)
                    dollar_toman = int(float(last_trade) / 10)
                    text += f"🇺🇸 دلار: {dollar_toman:,} تومان\n"

            # 2. Fetch Gold and Euro from Bonbast (scraping or public json)
            async with session.get("https://www.bonbast.com/json", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Bonbast json keys
                    euro = data.get('eur', {}).get('value', 0)
                    gold18 = data.get('gol18', {}).get('value', 0)
                    gold24 = data.get('gol24', {}).get('value', 0)
                    emami = data.get('sekke', {}).get('value', 0)
                    
                    text += f"🇪🇺 یورو: {euro:,} تومان\n"
                    text += f"🥇 طلا ۱۸ عیار: {gold18:,} تومان\n"
                    text += f"🥇 طلا ۲۴ عیار: {gold24:,} تومان\n"
                    text += f"🪙 سکه امامی: {emami:,} تومان\n"
                    
        text += "\n📊 منبع: نوبیتکس و بون‌بست"
        return text
    except Exception as e:
        print(f"Currency error: {e}")
    return "❌ خطا در دریافت قیمت‌ها."

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}(قیمت ارز|دلار|قیمت دلار)$"))
    async def dollar_cmd(event: events.NewMessage.Event) -> None:
        await event.edit("⏳ در حال دریافت قیمت‌های لحظه‌ای...")
        price_text = await get_live_prices()
        await event.edit(price_text)
