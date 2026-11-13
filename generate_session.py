from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = 2040
api_hash = 'b18441a1ff607e10a989891a5462e627'

print("Starting login process...")
with TelegramClient(StringSession(), api_id, api_hash) as client:
    client.start()
    print("\n=============================================")
    print("YOUR SESSION STRING (copy everything between the lines):")
    print("---------------------------------------------")
    print(client.session.save())
    print("=============================================\n")
