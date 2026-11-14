"""Currency plugin: `.دلار` fetches live dollar price from Nobitex."""
import aiohttp
from telethon import events
from selfbot.config import config

import re

async def get_live_prices():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    text = "💵 **قیمت‌های لحظه‌ای بازار:**\n\n"
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            # Scraping Iranjib
            async with session.get("https://iranjib.ir/", timeout=15) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    
                    # Iranjib structure: usually <td class="...">...</td>
                    # We will use regex to find prices near specific keywords
                    # Dollar
                    match_usd = re.search(r'دلار.*?<td[^>]*>(.*?)</td>', html, re.DOTALL | re.IGNORECASE)
                    if match_usd:
                        usd = re.sub(r'<[^>]+>', '', match_usd.group(1)).strip()
                        text += f"🇺🇸 دلار: {usd} تومان\n"
                        
                    # Euro
                    match_eur = re.search(r'یورو.*?<td[^>]*>(.*?)</td>', html, re.DOTALL | re.IGNORECASE)
                    if match_eur:
                        eur = re.sub(r'<[^>]+>', '', match_eur.group(1)).strip()
                        text += f"🇪🇺 یورو: {eur} تومان\n"
                        
                    # Gold 18k
                    match_gold = re.search(r'طلای 18 عیار.*?<td[^>]*>(.*?)</td>', html, re.DOTALL | re.IGNORECASE)
                    if match_gold:
                        gold = re.sub(r'<[^>]+>', '', match_gold.group(1)).strip()
                        text += f"🥇 طلا ۱۸ عیار: {gold} تومان\n"
                        
                    # Emami Coin
                    match_coin = re.search(r'سکه امامی.*?<td[^>]*>(.*?)</td>', html, re.DOTALL | re.IGNORECASE)
                    if match_coin:
                        coin = re.sub(r'<[^>]+>', '', match_coin.group(1)).strip()
                        text += f"🪙 سکه امامی: {coin} تومان\n"
                        
                    if "دلار" in text and "یورو" in text:
                        text += "\n📊 منبع: ایران‌جیب"
                        return text
    except Exception as e:
        print(f"Iranjib scraping error: {e}")
        
    # Fallback to Nobitex if Iranjib fails
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get("https://api.nobitex.ir/v2/orderbook/USDTIRT", timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    last_trade = data.get('lastTradePrice', 0)
                    dollar_toman = int(float(last_trade) / 10)
                    return f"💵 **قیمت‌های لحظه‌ای بازار:**\n\n🇺🇸 دلار (تتر): {dollar_toman:,} تومان\n\n📊 منبع: نوبیتکس (ایران‌جیب در دسترس نیست)"
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
