# Jesus Self

A modular Telegram selfbot built with Telethon, inspired by the features of @SelfSazXxbot.

## WARNING
Selfbots use your personal account via MTProto. This violates Telegram ToS and may get your account banned. Use a burner account.

## Features

- Timed media saver: auto-saves self-destructing photos/videos in DMs
- Text to Voice: `.say <text>` sends the text as a voice note via gTTS
- Song search: `.song <name>` searches YouTube and sends the audio via yt-dlp
- Core: `.help`, `.ping`, `.info`
- Plugin system: drop a file in `selfbot/plugins/` with a `register(client)` function and it loads automatically

## Setup

1. Get `API_ID` and `API_HASH` from https://my.telegram.org
2. Copy `.env.example` to `.env` and fill it in
3. Install deps: `pip install -r requirements.txt`
4. (Windows, for mp3) install FFmpeg and add it to PATH
5. Run: `python main.py`

On first run Telethon asks for your phone number and OTP.

## Structure

- `main.py` — entry point
- `selfbot/config.py` — .env loader
- `selfbot/client.py` — Telethon client factory
- `selfbot/loader.py` — dynamic plugin loader
- `selfbot/plugins/core.py` — `.help` `.ping` `.info`
- `selfbot/plugins/saver.py` — timed media saver
- `selfbot/plugins/voice.py` — `.say` (TTS)
- `selfbot/plugins/music.py` — `.song` (yt-dlp)

## Adding a new feature

Create `selfbot/plugins/myfeature.py` exposing a `register(client)` function that registers an event handler. Restart and it is loaded automatically.
