import asyncpg
import os
import asyncio
from cryptography.fernet import Fernet

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Generate a key (in production, keep this in .env)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print("[WARN] ENCRYPTION_KEY not set; generated a temporary one. Stored sessions cannot be decrypted after restart.")
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL is not set in environment variables.")

pool = None
_init_lock = asyncio.Lock()

async def init_db():
    global pool
    if pool is not None:
        return
    async with _init_lock:
        if pool is not None:
            return
        pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=20, statement_cache_size=0, command_timeout=15)
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
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS fishing_active INTEGER DEFAULT 0")
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS fishing_interval TEXT")
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS save_cat_active INTEGER DEFAULT 0")
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS save_cat_announce INTEGER DEFAULT 0")
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS save_cat_scanning INTEGER DEFAULT 0")
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS meow_interval TEXT')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS calc_on INTEGER DEFAULT 1')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS trans_on INTEGER DEFAULT 1')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS g_deleted INTEGER DEFAULT 1')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS g_selfdestruct INTEGER DEFAULT 1')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS g_edited INTEGER DEFAULT 1')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS secretary_on INTEGER DEFAULT 0')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS secretary_text TEXT')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS lock_pv INTEGER DEFAULT 0')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS always_online INTEGER DEFAULT 0')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS always_typing INTEGER DEFAULT 0')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS auto_seen INTEGER DEFAULT 0')
            await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS muted_users BIGINT[] DEFAULT \'{}\'')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS enemies (
                    user_id BIGINT NOT NULL,
                    enemy_id BIGINT NOT NULL,
                    enemy_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, enemy_id)
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS curses (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

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
                print(f"[DB] session decrypt failed for {user_id}; user must re-login.")
                return None
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

async def set_fishing_active(user_id, is_active):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS fishing_active INTEGER DEFAULT 0')
        await conn.execute('UPDATE users SET fishing_active = $1 WHERE user_id = $2', is_active, user_id)

async def get_fishing_active(user_id):
    await init_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT fishing_active FROM users WHERE user_id = $1', user_id)
        return bool(row['fishing_active']) if row and row['fishing_active'] else False

FISH_RARITIES = ("legendary", "epic", "rare", "common")
FISH_MODES = ("sell", "cat", "fridge")

async def set_fish_mode(user_id, rarity, mode):
    await init_db()
    if rarity not in FISH_RARITIES:
        return
    async with pool.acquire() as conn:
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS fish_mode_" + rarity + " TEXT")
        await conn.execute(f"UPDATE users SET fish_mode_{rarity} = $1 WHERE user_id = $2", mode, user_id)

async def get_fish_modes(user_id):
    await init_db()
    async with pool.acquire() as conn:
        for r in FISH_RARITIES:
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS fish_mode_" + r + " TEXT")
        row = await conn.fetchrow("SELECT fish_mode_legendary, fish_mode_epic, fish_mode_rare, fish_mode_common FROM users WHERE user_id = $1", user_id)
        out = {}
        for r in FISH_RARITIES:
            v = row['fish_mode_' + r] if row else None
            out[r] = v or "sell"
        return out


async def get_all_fishing_active_users():
    await init_db()
    async with pool.acquire() as conn:
        return await conn.fetch('SELECT user_id, meow_chat_id, meow_chat_title FROM users WHERE fishing_active = 1')

async def set_fishing_interval(user_id, interval_str):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS fishing_interval TEXT')
        await conn.execute('UPDATE users SET fishing_interval = $1 WHERE user_id = $2', interval_str, user_id)

async def get_fishing_interval(user_id):
    await init_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT fishing_interval FROM users WHERE user_id = $1', user_id)
        return row['fishing_interval'] if row and row['fishing_interval'] else None

async def set_save_cat_active(user_id, is_active):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS save_cat_active INTEGER DEFAULT 0")
        await conn.execute("UPDATE users SET save_cat_active = $1 WHERE user_id = $2", is_active, user_id)

async def get_save_cat_active(user_id):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS save_cat_active INTEGER DEFAULT 0")
        row = await conn.fetchrow("SELECT save_cat_active FROM users WHERE user_id = $1", user_id)
        return bool(row['save_cat_active']) if row and row['save_cat_active'] else False

async def set_save_cat_scanning(user_id, on):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS save_cat_scanning INTEGER DEFAULT 0")
        await conn.execute("UPDATE users SET save_cat_scanning = $1 WHERE user_id = $2", on, user_id)

async def get_save_cat_scanning(user_id):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS save_cat_scanning INTEGER DEFAULT 0")
        row = await conn.fetchrow("SELECT save_cat_scanning FROM users WHERE user_id = $1", user_id)
        return bool(row['save_cat_scanning']) if row and row['save_cat_scanning'] else False

async def set_save_cat_announce(user_id, on):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS save_cat_announce INTEGER DEFAULT 0")
        await conn.execute("UPDATE users SET save_cat_announce = $1 WHERE user_id = $2", on, user_id)

async def get_save_cat_announce(user_id):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS save_cat_announce INTEGER DEFAULT 0")
        row = await conn.fetchrow("SELECT save_cat_announce FROM users WHERE user_id = $1", user_id)
        return bool(row['save_cat_announce']) if row and row['save_cat_announce'] else False

async def get_all_save_cat_active_users():
    await init_db()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT user_id FROM users WHERE save_cat_active = 1")

async def get_meow_interval(user_id):
    await init_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT meow_interval FROM users WHERE user_id = $1', user_id)
        return row['meow_interval'] if row and row['meow_interval'] else None

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

async def get_feature_flags(user_id):
    await init_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT calc_on, trans_on, g_deleted, g_selfdestruct, g_edited FROM users WHERE user_id = $1",
            user_id,
        )
        if not row:
            return {"calc_on": True, "trans_on": True, "g_deleted": True, "g_selfdestruct": True, "g_edited": True}
        return {
            "calc_on": bool(row["calc_on"]),
            "trans_on": bool(row["trans_on"]),
            "g_deleted": bool(row["g_deleted"]),
            "g_selfdestruct": bool(row["g_selfdestruct"]),
            "g_edited": bool(row["g_edited"]),
        }


async def toggle_feature(user_id, column, default=1):
    """Flip a boolean feature column for a user. Returns new value."""
    await init_db()
    allowed = {"calc_on", "trans_on", "g_deleted", "g_selfdestruct", "g_edited"}
    if column not in allowed:
        raise ValueError("bad column")
    async with pool.acquire() as conn:
        # ensure row exists
        await conn.execute('INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING', user_id)
        row = await conn.fetchrow(f"SELECT {column} FROM users WHERE user_id = $1", user_id)
        cur = row[column] if row else default
        new = 0 if cur else 1
        await conn.execute(f"UPDATE users SET {column} = $1 WHERE user_id = $2", new, user_id)
        return bool(new)


async def set_feature(user_id, column, value: bool):
    await init_db()
    allowed = {"calc_on", "trans_on", "g_deleted", "g_selfdestruct", "g_edited"}
    if column not in allowed:
        raise ValueError("bad column")
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING', user_id)
        await conn.execute(f"UPDATE users SET {column} = $1 WHERE user_id = $2", 1 if value else 0, user_id)


async def get_all_active_users():
    await init_db()
    async with pool.acquire() as conn:
        return await conn.fetch('SELECT * FROM users WHERE is_active = 1')

async def deduct_yaqoot(user_id, amount):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET yaqoot_balance = yaqoot_balance - $1, last_deduction = CURRENT_TIMESTAMP WHERE user_id = $2', amount, user_id)

async def get_setting(user_id, col, default=None):
    await init_db()
    allowed = {"secretary_on","secretary_text","lock_pv","always_online","always_typing","auto_seen"}
    if col not in allowed:
        raise ValueError("bad col")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT {col} FROM users WHERE user_id = $1", user_id)
        return row[col] if row and row[col] is not None else default

async def set_setting(user_id, col, value):
    await init_db()
    allowed = {"secretary_on","secretary_text","lock_pv","always_online","always_typing","auto_seen"}
    if col not in allowed:
        raise ValueError("bad col")
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING', user_id)
        await conn.execute(f"UPDATE users SET {col} = $1 WHERE user_id = $2", value, user_id)

async def toggle_setting(user_id, col):
    cur = await get_setting(user_id, col, 0)
    new = 0 if cur else 1
    await set_setting(user_id, col, new)
    return bool(new)

async def add_muted(user_id, target_id):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING', user_id)
        await conn.execute('UPDATE users SET muted_users = array_append(COALESCE(muted_users, \'{}\'), $1) WHERE user_id = $2 AND NOT ($1 = ANY(COALESCE(muted_users, \'{}\')))', target_id, user_id)

async def remove_muted(user_id, target_id):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET muted_users = array_remove(COALESCE(muted_users, \'{}\'), $1) WHERE user_id = $2', target_id, user_id)

async def get_muted(user_id):
    await init_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT muted_users FROM users WHERE user_id = $1', user_id)
        return list(row['muted_users'] or []) if row else []

async def is_muted(user_id, target_id):
    m = await get_muted(user_id)
    return target_id in m


async def add_enemy(user_id, enemy_id, enemy_name):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO enemies (user_id, enemy_id, enemy_name) VALUES ($1, $2, $3)
            ON CONFLICT (user_id, enemy_id) DO UPDATE SET enemy_name = $3
        ''', user_id, enemy_id, enemy_name)

async def remove_enemy(user_id, enemy_id):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM enemies WHERE user_id = $1 AND enemy_id = $2', user_id, enemy_id)

async def get_enemies(user_id):
    await init_db()
    async with pool.acquire() as conn:
        return await conn.fetch('SELECT enemy_id, enemy_name FROM enemies WHERE user_id = $1 ORDER BY created_at DESC', user_id)

async def is_enemy(user_id, enemy_id):
    await init_db()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT 1 FROM enemies WHERE user_id = $1 AND enemy_id = $2', user_id, enemy_id)
        return row is not None

async def add_curse(user_id, text):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('INSERT INTO curses (user_id, text) VALUES ($1, $2)', user_id, text)

async def get_curses(user_id):
    await init_db()
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT text FROM curses WHERE user_id = $1', user_id)
        return [r['text'] for r in rows]

async def remove_curse(user_id, text):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM curses WHERE user_id = $1 AND text = $2', user_id, text)

async def clear_curses(user_id):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('DELETE FROM curses WHERE user_id = $1', user_id)


async def deactivate_user(user_id):
    await init_db()
    async with pool.acquire() as conn:
        await conn.execute('UPDATE users SET is_active = 0 WHERE user_id = $1', user_id)
