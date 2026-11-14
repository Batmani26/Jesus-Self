"""Currency plugin: `.دلار` fetches live dollar price from Nobitex."""
import aiohttp
from telethon import events
from selfbot.config import config

async def get_dollar_price():
    url = "https://api.nobitex.ir/v2/orderbook/USDTIRT"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Nobitex returns price in Rials (IRT). We divide by 10 for Toman.
                    last_trade = data.get('lastTradePrice', 0)
                    if last_trade:
                        toman = int(float(last_trade) / 10)
                        return f"💵 **قیمت دلار (تتر):** {toman:,} تومان"
    except Exception as e:
        print(f"Currency error: {e}")
    return "❌ خطا در دریافت قیمت دلار."

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}(دلار|قیمت دلار)$"))
    async def dollar_cmd(event: events.NewMessage.Event) -> None:
        await event.edit("⏳ در حال دریافت قیمت لحظه‌ای...")
        price_text = await get_dollar_price()
        await event.edit(price_text)
