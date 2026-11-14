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
            # Direct JSON from a highly reliable Iranian API
            async with session.get("https://api.tgju.org/v1/market/indicator/summary-table-data/price_dollar_rl", timeout=10) as resp:
                # If tgju works
                pass
                
            # Using the public Bonbast API (often reliable)
            async with session.get("https://www.bonbast.com/json", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    dollar = data.get('usd', {}).get('value', 0)
                    euro = data.get('eur', {}).get('value', 0)
                    gold18 = data.get('gol18', {}).get('value', 0)
                    gold24 = data.get('gol24', {}).get('value', 0)
                    emami = data.get('sekke', {}).get('value', 0)
                    
                    text += f"🇺🇸 دلار: {dollar:,} تومان\n"
                    text += f"🇪🇺 یورو: {euro:,} تومان\n"
                    text += f"🥇 طلا ۱۸ عیار: {gold18:,} تومان\n"
                    text += f"🥇 طلا ۲۴ عیار: {gold24:,} تومان\n"
                    text += f"🪙 سکه امامی: {emami:,} تومان\n"
                    text += "\n📊 منبع: بون‌بست"
                    return text
                    
            # Fallback to Nobitex
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
