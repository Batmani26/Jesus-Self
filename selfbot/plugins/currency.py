"""Currency plugin: Fetches live prices from Nobitex and TGJU."""
import aiohttp
import re
from telethon import events
from selfbot.config import config

async def get_live_prices():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
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
                else:
                    text += "🇺🇸 دلار: نامشخص\n"

            # 2. Fetch Gold and Euro from TGJU using an internal API
            async with session.get("https://api.tgju.org/v1/market/indicator/summary-table-data/geram18", timeout=10) as resp2:
                if resp2.status == 200:
                    data = await resp2.json()
                    gold_price = data.get('data', [{}])[0].get('p', 'نامشخص')
                    text += f"🥇 طلا ۱۸ عیار: {gold_price} تومان\n"
            
            async with session.get("https://api.tgju.org/v1/market/indicator/summary-table-data/price_eur", timeout=10) as resp3:
                if resp3.status == 200:
                    data = await resp3.json()
                    euro_price = data.get('data', [{}])[0].get('p', 'نامشخص')
                    text += f"🇪🇺 یورو: {euro_price} تومان\n"
            
            async with session.get("https://api.tgju.org/v1/market/indicator/summary-table-data/sekee", timeout=10) as resp4:
                if resp4.status == 200:
                    data = await resp4.json()
                    emami_price = data.get('data', [{}])[0].get('p', 'نامشخص')
                    text += f"🪙 سکه امامی: {emami_price} تومان\n"
            
            text += "\n📊 منبع: نوبیتکس و TGJU"
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
