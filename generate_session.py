from telethon.sync import TelegramClient
from telethon.sessions import StringSession

import os
from dotenv import load_dotenv
load_dotenv()
api_id = int(os.getenv("API_ID", "0"))
api_hash = os.getenv("API_HASH", "")
if not api_id or not api_hash:
    raise SystemExit("API_ID / API_HASH missing in .env")

print("Starting login process...")
with TelegramClient(StringSession(), api_id, api_hash) as client:
    client.start()
    print("\n=============================================")
    print("YOUR SESSION STRING (copy everything between the lines):")
    print("---------------------------------------------")
    print(client.session.save())
    print("=============================================\n")
