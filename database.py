# database.py
# مدیریت دیتابیس SQLite

import sqlite3
from datetime import datetime, timedelta
from config import DATABASE_NAME, AD_PRICE_PER_DAY

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    
    # جدول ریمیکس‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS remixes (
        code INTEGER PRIMARY KEY,
        file_path TEXT NOT NULL,
        title TEXT,
        artist TEXT,
        cover_path TEXT,
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        dislikes INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # جدول کانال‌های عضویت اجباری
    c.execute('''CREATE TABLE IF NOT EXISTS required_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_link TEXT NOT NULL,
        display_name TEXT NOT NULL,
        expires_at TIMESTAMP,
        is_active INTEGER DEFAULT 1
    )''')
    
    # جدول ادمین‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        added_by INTEGER,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # جدول کاربران و ریمیکس‌های دریافت شده
    c.execute('''CREATE TABLE IF NOT EXISTS user_remixes (
        user_id INTEGER,
        remix_code INTEGER,
        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, remix_code)
    )''')
    
    # جدول رای‌ها (پیشنهاد 👍👎)
    c.execute('''CREATE TABLE IF NOT EXISTS remix_votes (
        user_id INTEGER,
        remix_code INTEGER,
        vote INTEGER,  -- 1 = 👍 , -1 = 👎
        voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, remix_code)
    )''')
    
    # جدول کاربران (برای ذخیره تمام کاربرانی که ربات را استارت کردند)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # جدول سیستم دعوت دوستان (پیشنهاد ۶)
    c.execute('''CREATE TABLE IF NOT EXISTS referrals (
        referrer_id INTEGER,
        referred_id INTEGER PRIMARY KEY,
        referred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS referral_rewards (
        user_id INTEGER PRIMARY KEY,
        reward_active_until TIMESTAMP,
        reward_type TEXT  -- 'referrer' or 'referred'
    )''')
    
    # جدول تنظیمات
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # اضافه کردن تنظیمات پیش‌فرض
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ad_price_per_day', ?)", (str(AD_PRICE_PER_DAY),))
    
    conn.commit()
    conn.close()

# ========== توابع ریمیکس ==========
def add_remix(code, file_path, title, artist, cover_path):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO remixes (code, file_path, title, artist, cover_path) VALUES (?, ?, ?, ?, ?)",
              (code, file_path, title, artist, cover_path))
    conn.commit()
    conn.close()

def get_remix(code):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT code, file_path, title, artist, cover_path, views, likes, dislikes, created_at FROM remixes WHERE code = ?", (code,))
    result = c.fetchone()
    conn.close()
    return result

def increment_views(code, user_id):
    """افزایش بازدید فقط اگر کاربر قبلاً این ریمیکس را دریافت نکرده باشد"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT 1 FROM user_remixes WHERE user_id = ? AND remix_code = ?", (user_id, code))
    exists = c.fetchone()
    if not exists:
        c.execute("UPDATE remixes SET views = views + 1 WHERE code = ?", (code,))
    conn.commit()
    conn.close()
    return not exists

def get_all_remixes():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT code, title, artist, views, likes, dislikes, created_at FROM remixes ORDER BY code DESC")
    results = c.fetchall()
    conn.close()
    return results

def get_top_remixes_by_views(limit=3):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT code, title, artist, views, likes, dislikes, created_at FROM remixes ORDER BY views DESC LIMIT ?", (limit,))
    results = c.fetchall()
    conn.close()
    return results

def get_top_remixes_by_likes(limit=3):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT code, title, artist, views, likes, dislikes, created_at, (likes - dislikes) as score FROM remixes ORDER BY score DESC LIMIT ?", (limit,))
    results = c.fetchall()
    conn.close()
    return results

def get_random_remix():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT code, title, artist, file_path FROM remixes ORDER BY RANDOM() LIMIT 1")
    result = c.fetchone()
    conn.close()
    return result

# ========== توابع رای‌دهی ==========
def get_user_vote(user_id, remix_code):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT vote FROM remix_votes WHERE user_id = ? AND remix_code = ?", (user_id, remix_code))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def set_user_vote(user_id, remix_code, vote):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    
    c.execute("SELECT vote FROM remix_votes WHERE user_id = ? AND remix_code = ?", (user_id, remix_code))
    old = c.fetchone()
    
    if old:
        old_vote = old[0]
        c.execute("UPDATE remix_votes SET vote = ? WHERE user_id = ? AND remix_code = ?", (vote, user_id, remix_code))
        if old_vote == 1 and vote == -1:
            c.execute("UPDATE remixes SET likes = likes - 1, dislikes = dislikes + 1 WHERE code = ?", (remix_code,))
        elif old_vote == -1 and vote == 1:
            c.execute("UPDATE remixes SET likes = likes + 1, dislikes = dislikes - 1 WHERE code = ?", (remix_code,))
        elif old_vote == 1 and vote == 0:
            c.execute("UPDATE remixes SET likes = likes - 1 WHERE code = ?", (remix_code,))
        elif old_vote == -1 and vote == 0:
            c.execute("UPDATE remixes SET dislikes = dislikes - 1 WHERE code = ?", (remix_code,))
    else:
        c.execute("INSERT INTO remix_votes (user_id, remix_code, vote) VALUES (?, ?, ?)", (user_id, remix_code, vote))
        if vote == 1:
            c.execute("UPDATE remixes SET likes = likes + 1 WHERE code = ?", (remix_code,))
        elif vote == -1:
            c.execute("UPDATE remixes SET dislikes = dislikes + 1 WHERE code = ?", (remix_code,))
    
    conn.commit()
    conn.close()

# ========== توابع کانال‌های عضویت ==========
def add_channel(channel_link, display_name, days):
    expires_at = datetime.now() + timedelta(days=days) if days > 0 else None
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO required_channels (channel_link, display_name, expires_at, is_active) VALUES (?, ?, ?, ?)",
              (channel_link, display_name, expires_at, 1))
    conn.commit()
    conn.close()

def remove_channel(channel_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM required_channels WHERE id = ?", (channel_id,))
    conn.commit()
    conn.close()

def get_active_channels():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT id, channel_link, display_name FROM required_channels WHERE is_active = 1 AND (expires_at IS NULL OR expires_at > datetime('now'))")
    results = c.fetchall()
    conn.close()
    return results

def deactivate_expired_channels():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("UPDATE required_channels SET is_active = 0 WHERE expires_at IS NOT NULL AND expires_at <= datetime('now')")
    conn.commit()
    conn.close()

def get_all_channels():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT id, channel_link, display_name, expires_at, is_active FROM required_channels ORDER BY id")
    results = c.fetchall()
    conn.close()
    return results

# ========== توابع ادمین ==========
def add_admin(user_id, added_by):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?, ?)", (user_id, added_by))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_admin(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_all_admins():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM admins")
    results = c.fetchall()
    conn.close()
    return [r[0] for r in results]

# ========== توابع کاربر ==========
def add_user(user_id, username, first_name):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
              (user_id, username, first_name))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    results = c.fetchall()
    conn.close()
    return [r[0] for r in results]

def has_user_received_remix(user_id, remix_code):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT 1 FROM user_remixes WHERE user_id = ? AND remix_code = ?", (user_id, remix_code))
    result = c.fetchone()
    conn.close()
    return result is not None

def add_user_remix(user_id, remix_code):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO user_remixes (user_id, remix_code) VALUES (?, ?)", (user_id, remix_code))
    conn.commit()
    conn.close()

def get_total_remix_downloads():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM user_remixes")
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

# ========== توابع سیستم دعوت (پیشنهاد ۶) ==========
def get_user_referral_code(user_id):
    return f"REF_{user_id}"

def add_referral(referrer_id, referred_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, referred_id))
    conn.commit()
    conn.close()

def count_referrals(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def has_referral_reward(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT reward_active_until FROM referral_rewards WHERE user_id = ? AND reward_active_until > datetime('now')", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def activate_referral_reward(user_id, days, reward_type):
    until = datetime.now() + timedelta(days=days)
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO referral_rewards (user_id, reward_active_until, reward_type) VALUES (?, ?, ?)",
              (user_id, until.isoformat(), reward_type))
    conn.commit()
    conn.close()

def check_and_activate_referral_rewards(user_id):
    """بررسی اگر کاربر ۵ دعوت داشته باشد، پاداش فعال می‌شود"""
    count = count_referrals(user_id)
    if count >= 5 and not has_referral_reward(user_id):
        activate_referral_reward(user_id, 10, 'referrer')
        return True
    return False

# ========== توابع آمار (پیشنهاد ۷) ==========
def get_stats():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM remixes")
    total_remixes = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM user_remixes")
    total_downloads = c.fetchone()[0]
    
    c.execute("SELECT code, title, artist, views FROM remixes ORDER BY views DESC LIMIT 1")
    most_viewed = c.fetchone()
    
    c.execute("SELECT code, title, artist, (likes - dislikes) as score FROM remixes ORDER BY score DESC LIMIT 1")
    most_liked = c.fetchone()
    
    c.execute("SELECT COUNT(*) FROM required_channels WHERE is_active = 1 AND (expires_at IS NULL OR expires_at > datetime('now'))")
    active_channels = c.fetchone()[0]
    
    conn.close()
    
    return {
        'total_users': total_users,
        'total_remixes': total_remixes,
        'total_downloads': total_downloads,
        'most_viewed': most_viewed,
        'most_liked': most_liked,
        'active_channels': active_channels
    }

# ========== توابع تنظیمات ==========
def get_setting(key):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def set_setting(key, value):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()