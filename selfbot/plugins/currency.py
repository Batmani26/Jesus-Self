"""Currency plugin: `.دلار` fetches live dollar price from Nobitex."""
import aiohttp
from telethon import events
from selfbot.config import config

async def get_live_prices():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    text = "💵 **قیمت‌های لحظه‌ای بازار:**\n\n"
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            # Primary: Nerkh.io API (free and reliable)
            async with session.get("https://api.nerkh.io/v1/prices", timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Assuming data format: [{'symbol': 'usd', 'price': 50000}, ...]
                    prices = {item['symbol']: item['price'] for item in data if 'symbol' in item}
                    dollar = prices.get('usd', 0)
                    euro = prices.get('eur', 0)
                    gold18 = prices.get('gold18', 0)
                    gold24 = prices.get('gold24', 0)
                    emami = prices.get('sekke', 0)
                    
                    text += f"🇺🇸 دلار: {int(dollar):,} تومان\n"
                    text += f"🇪🇺 یورو: {int(euro):,} تومان\n"
                    text += f"🥇 طلا ۱۸ عیار: {int(gold18):,} تومان\n"
                    text += f"🥇 طلا ۲۴ عیار: {int(gold24):,} تومان\n"
                    text += f"🪙 سکه امامی: {int(emami):,} تومان\n"
                    text += "\n📊 منبع: نرخ‌آی‌او"
                    return text
                    
            # Fallback: Nobitex for Dollar
            async with session.get("https://api.nobitex.ir/v2/orderbook/USDTIRT", timeout=10) as resp2:
                if resp2.status == 200:
                    data = await resp2.json()
                    last_trade = data.get('lastTradePrice', 0)
                    dollar_toman = int(float(last_trade) / 10)
                    text += f"🇺🇸 دلار (تتر): {dollar_toman:,} تومان\n"
                    text += "\n📊 منبع: نوبیتکس (سایر قیمت‌ها در دسترس نیست)"
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
