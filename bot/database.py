import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # جدول کاربران ربات مدیریت
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            phone_number TEXT,
            session_string TEXT,
            is_active INTEGER DEFAULT 0,
            yaqoot_balance INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)
    ''', (user_id, username, first_name))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def set_user_phone(user_id, phone):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET phone_number = ? WHERE user_id = ?', (phone, user_id))
    conn.commit()
    conn.close()

def get_yaqoot(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT yaqoot_balance FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def add_yaqoot(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET yaqoot_balance = yaqoot_balance + ? WHERE user_id = ?', (amount, user_id))
    if cursor.rowcount == 0:
        # اگه کاربر وجود نداشت، با موجودی اولیه اضافه کن
        cursor.execute('INSERT INTO users (user_id, yaqoot_balance) VALUES (?, ?)', (user_id, amount))
    conn.commit()
    conn.close()

def save_session(user_id, session_string):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET session_string = ?, is_active = 1 WHERE user_id = ?', (session_string, user_id))
    conn.commit()
    conn.close()

init_db()
