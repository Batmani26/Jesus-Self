import asyncio
from bot.main import bot

async def main():
    try:
        me = await bot.get_me()
        print(f"Bot OK: @{me.username}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
