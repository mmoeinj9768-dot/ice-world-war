# database.py
# مدیریت دیتابیس SQLite

import sqlite3
from datetime import datetime, timedelta
from config import DATABASE_NAME, AD_PRICE_PER_DAY, CHANNEL_USERNAME

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
        is_active INTEGER DEFAULT 1,
        is_permanent INTEGER DEFAULT 0
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
    
    # جدول رای‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS remix_votes (
        user_id INTEGER,
        remix_code INTEGER,
        vote INTEGER,
        voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, remix_code)
    )''')
    
    # جدول کاربران
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # جدول دعوت‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS referrals (
        referrer_id INTEGER,
        referred_id INTEGER PRIMARY KEY,
        referred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # جدول پاداش دعوت
    c.execute('''CREATE TABLE IF NOT EXISTS referral_rewards (
        user_id INTEGER PRIMARY KEY,
        reward_active_until TIMESTAMP,
        reward_type TEXT
    )''')
    
    # جدول تنظیمات
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # جدول درخواست‌های آهنگ
    c.execute('''CREATE TABLE IF NOT EXISTS song_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        file_id TEXT,
        file_name TEXT,
        status TEXT DEFAULT 'pending',
        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, requested_at)
    )''')
    
    # جدول امتیاز
    c.execute('''CREATE TABLE IF NOT EXISTS user_points (
        user_id INTEGER PRIMARY KEY,
        points INTEGER DEFAULT 0,
        week_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS weekly_winners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        points INTEGER,
        week_start TIMESTAMP,
        won_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # جدول وضعیت قابلیت‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS bot_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # تنظیمات پیش‌فرض قابلیت‌ها
    default_features = [
        ('feature_get_by_code', 'on'),
        ('feature_song_request', 'on'),
        ('feature_random_remix', 'on'),
        ('feature_top_remixes', 'on'),
        ('feature_help', 'on'),
    ]
    for key, value in default_features:
        c.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)", (key, value))
    
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ad_price_per_day', ?)", (str(AD_PRICE_PER_DAY),))
    
    # ===== حذف رکوردهای تکراری کانال اصلی =====
    channel_link = f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"
    
    # ابتدا رکوردهای تکراری را حذف می‌کنیم (به جز یکی)
    c.execute('''
        DELETE FROM required_channels 
        WHERE channel_link = ? 
        AND id NOT IN (
            SELECT MIN(id) 
            FROM required_channels 
            WHERE channel_link = ?
        )
    ''', (channel_link, channel_link))
    
    # سپس کانال اصلی را اضافه می‌کنیم (اگر وجود نداشت)
    c.execute("INSERT OR IGNORE INTO required_channels (channel_link, display_name, expires_at, is_active, is_permanent) VALUES (?, ?, ?, ?, ?)",
              (channel_link, "کانال اصلی", None, 1, 1))
    
    conn.commit()
    conn.close()


# ============================================================
# توابع ریمیکس
# ============================================================
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

def delete_remix(code):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM remixes WHERE code = ?", (code,))
    c.execute("DELETE FROM user_remixes WHERE remix_code = ?", (code,))
    c.execute("DELETE FROM remix_votes WHERE remix_code = ?", (code,))
    conn.commit()
    conn.close()

def increment_views(code, user_id):
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


# ============================================================
# توابع رای‌دهی + امتیاز
# ============================================================
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
            add_points(user_id, 1, "like")
        elif vote == -1:
            c.execute("UPDATE remixes SET dislikes = dislikes + 1 WHERE code = ?", (remix_code,))
            add_points(user_id, -1, "dislike")
    
    conn.commit()
    conn.close()


# ============================================================
# توابع کانال‌های عضویت
# ============================================================
def add_channel(channel_link, display_name, days):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT id FROM required_channels WHERE channel_link = ? AND is_active = 1 AND (expires_at IS NULL OR expires_at > datetime('now'))", (channel_link,))
    existing = c.fetchone()
    if existing:
        conn.close()
        return False
    
    expires_at = datetime.now() + timedelta(days=days) if days > 0 else None
    c.execute("INSERT INTO required_channels (channel_link, display_name, expires_at, is_active, is_permanent) VALUES (?, ?, ?, ?, ?)",
              (channel_link, display_name, expires_at, 1, 0))
    conn.commit()
    conn.close()
    return True

def remove_channel(channel_id, is_owner=False):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT is_permanent FROM required_channels WHERE id = ?", (channel_id,))
    result = c.fetchone()
    if result and result[0] == 1 and not is_owner:
        conn.close()
        return False
    c.execute("DELETE FROM required_channels WHERE id = ?", (channel_id,))
    conn.commit()
    conn.close()
    return True

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
    c.execute("UPDATE required_channels SET is_active = 0 WHERE expires_at IS NOT NULL AND expires_at <= datetime('now') AND is_permanent = 0")
    conn.commit()
    conn.close()

def get_all_channels():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT id, channel_link, display_name, expires_at, is_active, is_permanent FROM required_channels ORDER BY id")
    results = c.fetchall()
    conn.close()
    return results


# ============================================================
# توابع ادمین
# ============================================================
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


# ============================================================
# توابع کاربران
# ============================================================
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

def get_user(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, joined_at FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result

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


# ============================================================
# توابع دعوت
# ============================================================
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
    count = count_referrals(user_id)
    if count >= 5 and not has_referral_reward(user_id):
        activate_referral_reward(user_id, 10, 'referrer')
        return True
    return False


# ============================================================
# توابع درخواست آهنگ
# ============================================================
def add_song_request(user_id, file_id, file_name):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO song_requests (user_id, file_id, file_name) VALUES (?, ?, ?)",
              (user_id, file_id, file_name))
    conn.commit()
    conn.close()

def get_last_song_request(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT requested_at FROM song_requests WHERE user_id = ? ORDER BY requested_at DESC LIMIT 1", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


# ============================================================
# توابع امتیاز
# ============================================================
def get_week_start():
    now = datetime.now()
    start = now - timedelta(days=now.weekday() + 1)
    return start.replace(hour=0, minute=0, second=0, microsecond=0)

def add_points(user_id, points, reason):
    week_start = get_week_start()
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    
    c.execute("SELECT points FROM user_points WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    if result:
        c.execute("UPDATE user_points SET points = points + ? WHERE user_id = ?", (points, user_id))
    else:
        c.execute("INSERT INTO user_points (user_id, points, week_start) VALUES (?, ?, ?)", (user_id, points, week_start))
    
    conn.commit()
    conn.close()

def get_user_points(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT points FROM user_points WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def reset_weekly_points():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    
    c.execute("SELECT user_id, points FROM user_points ORDER BY points DESC LIMIT 5")
    top_users = c.fetchall()
    
    week_start = get_week_start()
    
    for user_id, points in top_users:
        if points > 0:
            c.execute("INSERT INTO weekly_winners (user_id, points, week_start) VALUES (?, ?, ?)",
                      (user_id, points, week_start))
    
    for i, (user_id, points) in enumerate(top_users[:3]):
        if points > 0:
            activate_referral_reward(user_id, 3, 'weekly_winner')
    
    c.execute("DELETE FROM user_points")
    
    conn.commit()
    conn.close()
    
    return top_users

def get_top_users(limit=5):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, points FROM user_points ORDER BY points DESC LIMIT ?", (limit,))
    results = c.fetchall()
    conn.close()
    return results

def get_weekly_winners():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, points, week_start FROM weekly_winners ORDER BY points DESC LIMIT 5")
    results = c.fetchall()
    conn.close()
    return results


# ============================================================
# توابع تنظیمات و قابلیت‌ها
# ============================================================
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

def get_feature_status(feature_key):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT value FROM bot_settings WHERE key = ?", (feature_key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 'on'

def set_feature_status(feature_key, status):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (feature_key, status))
    conn.commit()
    conn.close()

def get_all_features():
    features = {
        'feature_get_by_code': 'دریافت ریمیکس با کد',
        'feature_song_request': 'پیشنهاد آهنگ برای ادیت',
        'feature_random_remix': 'ریمیکس تصادفی',
        'feature_top_remixes': 'ریمیکس‌های برتر',
        'feature_help': 'راهنما',
    }
    result = {}
    for key, name in features.items():
        status = get_feature_status(key)
        result[key] = {'name': name, 'status': status}
    return result

def is_feature_enabled(feature_key):
    return get_feature_status(feature_key) == 'on'


# ============================================================
# توابع آمار کامل
# ============================================================
def get_stats():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM remixes")
    total_remixes = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM user_remixes")
    total_downloads = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM required_channels WHERE is_active = 1 AND (expires_at IS NULL OR expires_at > datetime('now'))")
    active_channels = c.fetchone()[0]
    
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT COUNT(*) FROM users WHERE DATE(joined_at) = ?", (today,))
    today_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM user_remixes WHERE DATE(received_at) = ?", (today,))
    today_downloads = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM song_requests WHERE DATE(requested_at) = ?", (today,))
    today_requests = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM song_requests")
    total_requests = c.fetchone()[0]
    
    c.execute("SELECT SUM(views) FROM remixes")
    total_views = c.fetchone()[0] or 0
    
    c.execute("SELECT code, title, artist, views FROM remixes ORDER BY views DESC LIMIT 1")
    most_viewed = c.fetchone()
    
    c.execute("SELECT code, title, artist, likes FROM remixes ORDER BY likes DESC LIMIT 1")
    most_liked = c.fetchone()
    
    conn.close()
    
    return {
        'total_users': total_users,
        'total_remixes': total_remixes,
        'total_downloads': total_downloads,
        'active_channels': active_channels,
        'today_users': today_users,
        'today_downloads': today_downloads,
        'today_requests': today_requests,
        'total_requests': total_requests,
        'total_views': total_views,
        'most_viewed': most_viewed,
        'most_liked': most_liked,
    }


# ============================================================
# توابع گزارش هفتگی
# ============================================================
def get_weekly_report():
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    
    c.execute("SELECT COUNT(*) FROM users WHERE joined_at > ?", (week_ago,))
    new_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM user_remixes WHERE received_at > ?", (week_ago,))
    new_downloads = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM song_requests WHERE requested_at > ?", (week_ago,))
    new_requests = c.fetchone()[0]
    
    c.execute("SELECT code, title, artist, views FROM remixes ORDER BY views DESC LIMIT 3")
    top_remixes = c.fetchall()
    
    conn.close()
    
    return {
        'new_users': new_users,
        'new_downloads': new_downloads,
        'new_requests': new_requests,
        'top_remixes': top_remixes,
    }