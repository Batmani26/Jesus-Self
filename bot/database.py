import asyncpg
import os
import asyncio
from cryptography.fernet import Fernet

# Generate a key (in production, keep this in .env)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

DB_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_p7egLwaNhv1F@ep-young-term-zaeho23i-pooler.c-2.eu-west-2.aws.neon.tech/neondb?sslmode=require")

pool = None

async def init_db():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(DB_URL, min_size=1, max_size=10, statement_cache_size=0)
        async with pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    phone_number TEXT,
                    session_string TEXT,
                    is_active INTEGER DEFAULT 0,
                    yaqoot_balance INTEGER DEFAULT 0,
                    last_deduction TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Add last_deduction if it doesn't exist (for existing tables)
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS last_deduction TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS meow_chat_id TEXT')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS meow_chat_title TEXT')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS meow_active INTEGER DEFAULT 0')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS meow_interval TEXT')

async def add_user(user_id, username, first_name):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (user_id, username, first_name) VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE SET username = $2, first_name = $3
        ''', user_id, username, first_name)

async def get_user(user_id):
    await init_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM users WHERE user_id = $1', user_id)
        return row

async def get_decrypted_session(user_id):
    await init_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT session_string FROM users WHERE user_id = $1', user_id)
        if row and row['session_string']:
            try:
                return cipher_suite.decrypt(row['session_string'].encode()).decode()
            except Exception:
                # Fallback for old plaintext sessions
                return row['session_string']
        return None

async def set_user_phone(user_id, phone):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET phone_number = $1 WHERE user_id = $2', phone, user_id)

async def get_yaqoot(user_id):
    await init_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT yaqoot_balance FROM users WHERE user_id = $1', user_id)
        return row['yaqoot_balance'] if row else 0

async def add_yaqoot(user_id, amount):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (user_id, yaqoot_balance) VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET yaqoot_balance = users.yaqoot_balance + $2
        ''', user_id, amount)

async def save_session(user_id, session_string):
    await init_db()
    encrypted_session = cipher_suite.encrypt(session_string.encode()).decode()
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET session_string = $1, is_active = 1 WHERE user_id = $2', encrypted_session, user_id)

async def set_user_active(user_id, is_active):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET is_active = $1 WHERE user_id = $2', is_active, user_id)

async def set_meow_active(user_id, is_active):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS meow_active INTEGER DEFAULT 0')
        await conn.execute('UPDATE users SET meow_active = $1 WHERE user_id = $2', is_active, user_id)

async def get_meow_active(user_id):
    await init_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT meow_active FROM users WHERE user_id = $1', user_id)
        return bool(row['meow_active']) if row and row['meow_active'] else False

async def get_all_meow_active_users():
    await init_db()
    async with pool.acquire() as conn:
        return await conn.fetch('SELECT user_id, meow_chat_id, meow_chat_title FROM users WHERE meow_active = 1')

async def set_meow_interval(user_id, interval_str):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS meow_interval TEXT')
        await conn.execute('UPDATE users SET meow_interval = $1 WHERE user_id = $2', interval_str, user_id)

async def get_meow_interval(user_id):
    await init_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT meow_interval FROM users WHERE user_id = $1', user_id)
        return row['meow_interval'] if row and row['meow_interval'] else "4:10"

async def set_meow_target_db(user_id, chat_id, chat_title):
    await init_db()
    async with pool.acquire() as conn:
        # Ensure user exists before updating
        await conn.execute('''
            INSERT INTO users (user_id, meow_chat_id, meow_chat_title) VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE SET meow_chat_id = $2, meow_chat_title = $3
        ''', user_id, chat_id, chat_title)

async def get_meow_target_db(user_id):
    await init_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT meow_chat_id, meow_chat_title FROM users WHERE user_id = $1', user_id)
        if row and row['meow_chat_id']:
            return {"chat_id": row['meow_chat_id'], "chat_title": row['meow_chat_title']}
        return None

async def get_all_active_users():
    await init_db()
    async with pool.acquire() as conn:
        return await conn.fetch('SELECT * FROM users WHERE is_active = 1')

async def deduct_yaqoot(user_id, amount):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET yaqoot_balance = yaqoot_balance - $1, last_deduction = CURRENT_TIMESTAMP WHERE user_id = $2', amount, user_id)

async def deactivate_user(user_id):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET is_active = 0 WHERE user_id = $1', user_id)
