"""Currency plugin: `.دلار` fetches live dollar price from Nobitex."""
import aiohttp
from telethon import events
from selfbot.config import config

async def get_live_prices():
    # We will use a public API that aggregates tgju data (or similar)
    url = "https://api.tgju.org/v1/market/indicator/summary-table-data/price_dollar_rl"
    # For gold and other currencies, we can fetch from a known public source
    # Since tgju doesn't have a single JSON for all, I'll use a community API
    url_all = "https://call1.tgju.org/ajax.json"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url_all, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # tgju ajax.json returns a complex dict. We need to extract key values.
                    # The keys are like 'price_dollar_rl', 'price_eur', 'geram24' (gold 18k), etc.
                    current = data.get('current', {})
                    
                    def get_price(key):
                        val = current.get(key, {}).get('p', '0')
                        try:
                            return f"{int(float(val)):,} تومان"
                        except:
                            return "نامشخص"
                            
                    dollar = get_price('price_dollar_rl')
                    euro = get_price('price_eur')
                    gold18 = get_price('geram18')
                    gold24 = get_price('geram24')
                    emami = get_price('sekee')
                    
                    text = (
                        "💵 **قیمت‌های لحظه‌ای بازار:**\n\n"
                        f"🇺🇸 دلار: {dollar}\n"
                        f"🇪🇺 یورو: {euro}\n"
                        f"🥇 طلا ۱۸ عیار (گرم): {gold18}\n"
                        f"🥇 طلا ۲۴ عیار (گرم): {gold24}\n"
                        f"🪙 سکه امامی: {emami}\n\n"
                        "📊 منبع: TGJU"
                    )
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
