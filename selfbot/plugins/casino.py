"""Casino plugin.

- `.کازینو`          → spins sequentially until a high score (value >= 43).
- `.کازینو فلک جک`   → maximum-speed spam: fires many casino dice in parallel
                       until a jackpot (3 identical 7s = value 64).
"""
import asyncio
from telethon import events
from telethon.tl.types import InputMediaDice
from selfbot.config import config

JACKPOT_VALUE = 43  # any 3 identical symbols (Telegram casino values 43..64 = triples)
HIGH_VALUE = 43     # high score threshold for classic .کازینو


def register(client) -> None:
    import re as _re
    _ep = _re.escape(config.PREFIX)
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{_ep}کازینو$"))
    async def casino_cmd(event: events.NewMessage.Event) -> None:
        await event.delete()
        for _ in range(500):
            try:
                msg = await client.send_message(event.chat_id, file=InputMediaDice("🎰"))
                if msg and msg.media and hasattr(msg.media, "value"):
                    val = msg.media.value
                    if isinstance(val, int) and val >= HIGH_VALUE:
                        return
                asyncio.create_task(msg.delete())
            except Exception as e:
                print(f"Casino error: {e}")
                await asyncio.sleep(0.1)

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^{_ep}جک پات$"))
    async def casino_jackpot_cmd(event: events.NewMessage.Event) -> None:
        """Max-speed parallel casino spam until jackpot (three 7s)."""
        chat_id = event.chat_id
        reply_to = event.reply_to_msg_id if event.is_reply else None
        try:
            await event.delete()
        except Exception:
            pass

        stop = asyncio.Event()
        winner_msg = {"msg": None}
        casts = {"n": 0}

        async def cast_one():
            if stop.is_set():
                return
            try:
                msg = await client.send_message(chat_id, file=InputMediaDice("🎰"), reply_to=reply_to)
                casts["n"] += 1
                val = None
                if msg and getattr(msg, "media", None) and hasattr(msg.media, "value"):
                    val = msg.media.value
                if isinstance(val, int) and val >= JACKPOT_VALUE:
                    # Jackpot — keep this message, stop everything
                    winner_msg["msg"] = msg
                    stop.set()
                    return
                # Not a jackpot: delete quietly in background
                asyncio.create_task(_safe_delete(msg))
            except Exception as e:
                msg_txt = str(e).lower()
                if "flood" in msg_txt or "wait" in msg_txt:
                    # Respect Telegram flood limits briefly then continue
                    await asyncio.sleep(1.5)
                else:
                    await asyncio.sleep(0.02)

        async def _safe_delete(msg):
            try:
                await msg.delete()
            except Exception:
                pass

        # Launch a rolling burst of concurrent casts until jackpot found.
        # Total attempt budget (safety), but concurrency keeps it extremely fast.
        CONCURRENCY = 20  # افزایش موازی‌سازی برای سرعت بیشتر
        while not stop.is_set():
            rounds += 1
            batch = [asyncio.create_task(cast_one()) for _ in range(CONCURRENCY)]
            try:
                await asyncio.wait(batch, timeout=8)
            except Exception:
                pass
            # Cancel any still-running batch tasks so we don't pile up
            for t in batch:
                if not t.done():
                    t.cancel()
            if stop.is_set():
                break
            # tiny breather between bursts to avoid hammering
            await asyncio.sleep(0.02)

        # No final message needed — just stop when jackpot is found
