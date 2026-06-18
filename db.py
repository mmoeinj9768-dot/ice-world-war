# database/db.py
# اتصال و مدیریت دیتابیس

import sqlite3
import shutil
from contextlib import contextmanager
from typing import Optional, List, Tuple, Any
from datetime import datetime
from config import DATABASE_NAME
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# Singleton Connection Pool
# ============================================================

_connection_pool = {}


def get_connection() -> sqlite3.Connection:
    """دریافت اتصال به دیتابیس"""
    
    if DATABASE_NAME not in _connection_pool:
        conn = sqlite3.connect(
            DATABASE_NAME,
            timeout=30,
            check_same_thread=False,
            isolation_level="DEFERRED"
        )
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA wal_autocheckpoint = 1000")
        conn.execute("PRAGMA synchronous = NORMAL")
        _connection_pool[DATABASE_NAME] = conn
        logger.info("✅ Database connection established")
    
    return _connection_pool[DATABASE_NAME]


@contextmanager
def transaction():
    """مدیریت تراکنش دیتابیس"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN IMMEDIATE")
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Transaction failed: {e}")
        raise
    finally:
        cursor.close()


def execute_query(query: str, params: tuple = ()) -> List[Tuple]:
    """اجرای یک کوئری SELECT"""
    with transaction() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def execute_write(query: str, params: tuple = ()) -> int:
    """اجرای یک کوئری نوشتاری (INSERT/UPDATE/DELETE)"""
    with transaction() as cursor:
        cursor.execute(query, params)
        return cursor.rowcount


# ============================================================
# توابع کمکی
# ============================================================

def get_pending_remix(user_id: int) -> Optional[int]:
    """دریافت کد ریمیکس معلق برای کاربر"""
    results = execute_query(
        "SELECT remix_code FROM pending_remixes WHERE user_id = ?",
        (user_id,)
    )
    return results[0][0] if results else None


def save_pending_remix(user_id: int, remix_code: int) -> None:
    """ذخیره درخواست معلق"""
    execute_write(
        "INSERT OR REPLACE INTO pending_remixes (user_id, remix_code) VALUES (?, ?)",
        (user_id, remix_code)
    )


def clear_pending_remix(user_id: int) -> None:
    """پاک کردن درخواست معلق"""
    execute_write(
        "DELETE FROM pending_remixes WHERE user_id = ?",
        (user_id,)
    )


def get_setting(key: str) -> Optional[str]:
    """دریافت تنظیمات"""
    results = execute_query(
        "SELECT value FROM settings WHERE key = ?",
        (key,)
    )
    return results[0][0] if results else None


def set_setting(key: str, value: str) -> None:
    """تنظیم مقدار"""
    execute_write(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value)
    )


def get_feature_status(feature_key: str) -> str:
    """دریافت وضعیت یک قابلیت"""
    results = execute_query(
        "SELECT value FROM bot_settings WHERE key = ?",
        (feature_key,)
    )
    return results[0][0] if results else 'on'


def set_feature_status(feature_key: str, status: str) -> None:
    """تغییر وضعیت یک قابلیت"""
    execute_write(
        "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)",
        (feature_key, status)
    )


def get_all_features() -> dict:
    """دریافت تمام قابلیت‌ها با وضعیت"""
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


def get_last_song_request(user_id: int) -> Optional[str]:
    """دریافت زمان آخرین درخواست آهنگ کاربر"""
    results = execute_query(
        "SELECT requested_at FROM song_requests WHERE user_id = ? ORDER BY requested_at DESC LIMIT 1",
        (user_id,)
    )
    return results[0][0] if results else None


def add_song_request(user_id: int, file_id: str, file_name: str) -> None:
    """ثبت درخواست آهنگ جدید"""
    execute_write(
        "INSERT INTO song_requests (user_id, file_id, file_name) VALUES (?, ?, ?)",
        (user_id, file_id, file_name)
    )


def backup_database() -> str:
    """ایجاد بکاپ از دیتابیس"""
    backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy(DATABASE_NAME, backup_name)
    logger.info(f"✅ Database backup created: {backup_name}")
    return backup_name


# ============================================================
# مقداردهی اولیه دیتابیس
# ============================================================

def init_db() -> None:
    """مقداردهی اولیه دیتابیس با تمام Migration‌ها و Indexها"""
    
    queries = [
        # ===== جداول اصلی =====
        """
        CREATE TABLE IF NOT EXISTS remixes (
            code INTEGER PRIMARY KEY,
            file_path TEXT NOT NULL,
            title TEXT,
            artist TEXT,
            cover_path TEXT,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            dislikes INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS required_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_link TEXT NOT NULL,
            chat_id TEXT,
            display_name TEXT NOT NULL,
            expires_at TEXT,
            is_active INTEGER DEFAULT 1,
            is_permanent INTEGER DEFAULT 0
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS user_remixes (
            user_id INTEGER,
            remix_code INTEGER,
            received_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, remix_code),
            FOREIGN KEY (remix_code) REFERENCES remixes(code) ON DELETE CASCADE
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS remix_votes (
            user_id INTEGER,
            remix_code INTEGER,
            vote INTEGER NOT NULL CHECK (vote IN (-1, 0, 1)),
            voted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, remix_code),
            FOREIGN KEY (remix_code) REFERENCES remixes(code) ON DELETE CASCADE
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS referrals (
            referrer_id INTEGER,
            referred_id INTEGER PRIMARY KEY,
            referred_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS referral_rewards (
            user_id INTEGER PRIMARY KEY,
            reward_active_until TEXT,
            reward_type TEXT
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS song_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            file_id TEXT,
            file_name TEXT,
            status TEXT DEFAULT 'pending',
            requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, requested_at)
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS user_points (
            user_id INTEGER PRIMARY KEY,
            points INTEGER DEFAULT 0,
            week_start TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS weekly_winners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            points INTEGER,
            week_start TEXT,
            won_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS pending_remixes (
            user_id INTEGER PRIMARY KEY,
            remix_code INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # ===== ایندکس‌ها =====
        """
        CREATE INDEX IF NOT EXISTS idx_remix_votes_remix ON remix_votes(remix_code)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_remix_votes_user ON remix_votes(user_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_user_remixes_user ON user_remixes(user_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_user_remixes_remix ON user_remixes(remix_code)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_song_requests_user ON song_requests(user_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_users_joined ON users(joined_at)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_remixes_views ON remixes(views DESC)
        """,
        
        # ===== تنظیمات پیش‌فرض =====
        """
        INSERT OR IGNORE INTO bot_settings (key, value) VALUES 
            ('feature_get_by_code', 'on'),
            ('feature_song_request', 'on'),
            ('feature_random_remix', 'on'),
            ('feature_top_remixes', 'on'),
            ('feature_help', 'on')
        """,
        
        """
        INSERT OR IGNORE INTO settings (key, value) VALUES ('ad_price_per_day', '50000')
        """,
    ]
    
    for query in queries:
        try:
            execute_write(query)
        except Exception as e:
            logger.warning(f"⚠️ Query failed: {e}")
    
    logger.info("✅ Database initialized successfully")