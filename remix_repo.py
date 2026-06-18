# database/remix_repo.py
# Repository برای جدول remixes

from database.db import execute_query, execute_write, get_connection
from typing import Optional, List, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


def add_remix(code: int, file_path: str, title: str, artist: str, cover_path: str) -> None:
    """افزودن ریمیکس جدید"""
    execute_write(
        "INSERT OR REPLACE INTO remixes (code, file_path, title, artist, cover_path) VALUES (?, ?, ?, ?, ?)",
        (code, file_path, title, artist, cover_path)
    )


def get_remix(code: int) -> Optional[Tuple]:
    """دریافت ریمیکس بر اساس کد"""
    results = execute_query(
        "SELECT code, file_path, title, artist, cover_path, views, likes, dislikes, created_at FROM remixes WHERE code = ?",
        (code,)
    )
    return results[0] if results else None


def delete_remix(code: int) -> None:
    """حذف ریمیکس"""
    execute_write("DELETE FROM remixes WHERE code = ?", (code,))


def get_all_remixes() -> List[Tuple]:
    """دریافت همه ریمیکس‌ها"""
    return execute_query(
        "SELECT code, title, artist, views, likes, dislikes, created_at FROM remixes ORDER BY code DESC"
    )


def get_top_remixes_by_views(limit: int = 3) -> List[Tuple]:
    """دریافت پربازدیدترین ریمیکس‌ها"""
    return execute_query(
        "SELECT code, title, artist, views, likes, dislikes, created_at FROM remixes ORDER BY views DESC LIMIT ?",
        (limit,)
    )


def get_top_remixes_by_likes(limit: int = 3) -> List[Tuple]:
    """دریافت پرلایک‌ترین ریمیکس‌ها"""
    return execute_query(
        "SELECT code, title, artist, views, likes, dislikes, created_at, (likes - dislikes) as score FROM remixes ORDER BY score DESC LIMIT ?",
        (limit,)
    )


def get_random_remix() -> Optional[Tuple]:
    """دریافت یک ریمیکس تصادفی"""
    results = execute_query(
        "SELECT code, title, artist, file_path FROM remixes ORDER BY RANDOM() LIMIT 1"
    )
    return results[0] if results else None


def increment_views(code: int, user_id: int) -> bool:
    """افزایش بازدید ریمیکس (Atomic)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN IMMEDIATE")
        
        cursor.execute(
            "INSERT OR IGNORE INTO user_remixes (user_id, remix_code) VALUES (?, ?)",
            (user_id, code)
        )
        
        if cursor.rowcount > 0:
            cursor.execute(
                "UPDATE remixes SET views = views + 1 WHERE code = ?",
                (code,)
            )
            conn.commit()
            return True
        
        conn.commit()
        return False
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error incrementing views: {e}")
        raise
    finally:
        cursor.close()


def get_total_remix_downloads() -> int:
    """دریافت تعداد کل دانلودها"""
    results = execute_query("SELECT COUNT(*) FROM user_remixes")
    return results[0][0] if results else 0


def add_referral(referrer_id: int, referred_id: int) -> None:
    """ثبت دعوت"""
    execute_write(
        "INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
        (referrer_id, referred_id)
    )


def count_referrals(user_id: int) -> int:
    """تعداد دعوت‌های کاربر"""
    results = execute_query(
        "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?",
        (user_id,)
    )
    return results[0][0] if results else 0


def get_weekly_report() -> dict:
    """دریافت گزارش هفتگی"""
    results = execute_query(
        "SELECT COUNT(*) FROM users WHERE joined_at > datetime('now', '-7 days')"
    )
    new_users = results[0][0] if results else 0
    
    results = execute_query(
        "SELECT COUNT(*) FROM user_remixes WHERE received_at > datetime('now', '-7 days')"
    )
    new_downloads = results[0][0] if results else 0
    
    results = execute_query(
        "SELECT COUNT(*) FROM song_requests WHERE requested_at > datetime('now', '-7 days')"
    )
    new_requests = results[0][0] if results else 0
    
    top_remixes = execute_query(
        "SELECT code, title, artist, views FROM remixes ORDER BY views DESC LIMIT 3"
    )
    
    return {
        'new_users': new_users,
        'new_downloads': new_downloads,
        'new_requests': new_requests,
        'top_remixes': top_remixes,
    }