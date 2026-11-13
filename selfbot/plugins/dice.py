"""Dice plugin: `.تاس <1-6>` edits the message to show a specific dice face."""
from telethon import events
from selfbot.config import config

DICE_FACES = {
    1: "⚀",
    2: "⚁",
    3: "⚂",
    4: "⚃",
    5: "⚄",
    6: "⚅"
}

def register(client) -> None:
    p = config.PREFIX

    @client.on(events.NewMessage(outgoing=True, pattern=rf"^\{p}تاس ([1-6])$"))
    async def dice_cmd(event: events.NewMessage.Event) -> None:
        num = int(event.pattern_match.group(1))
        face = DICE_FACES[num]
        await event.edit(f"🎲 **نتیجه تاس:** {face} ({num})")
