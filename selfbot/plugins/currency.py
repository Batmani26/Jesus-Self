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
                    text += f"🇺🇸 دلار (تتر): {dollar_toman:,} تومان\n"
                else:
                    text += "🇺🇸 دلار: نامشخص\n"

            # 2. Fetch Gold and Euro from TGJU (using their open API)
            tgju_url = "https://api.tgju.org/v1/market/indicator/summary-table-data"
            # TGJU blocks some IPs, so we try another free public API for gold
            async with session.get("https://api.navasan.ir/v1/market/price", timeout=10) as resp2:
                if resp2.status == 200:
                    data = await resp2.json()
                    # Navasan API keys
                    euro = data.get('eur', {}).get('value', 0)
                    gold18 = data.get('gold18', {}).get('value', 0)
                    gold24 = data.get('gold24', {}).get('value', 0)
                    emami = data.get('sekke', {}).get('value', 0)
                    
                    text += f"🇪🇺 یورو: {euro:,} تومان\n"
                    text += f"🥇 طلا ۱۸ عیار: {gold18:,} تومان\n"
                    text += f"🥇 طلا ۲۴ عیار: {gold24:,} تومان\n"
                    text += f"🪙 سکه امامی: {emami:,} تومان\n"
                else:
                    text += "🥇 طلا و یورو: در دسترس نیست.\n"
                    
        text += "\n📊 منبع: نوبیتکس و نوسان"
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
