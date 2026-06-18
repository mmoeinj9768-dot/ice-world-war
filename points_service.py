# services/points_service.py
# سرویس امتیاز

from database.db import execute_write, execute_query
from datetime import datetime, timedelta
from utils.logger import get_logger
from utils.cache import CacheManager

logger = get_logger(__name__)


def add_points(user_id: int, points: int, reason: str) -> None:
    """اضافه کردن امتیاز به کاربر (Atomic)"""
    week_start = get_week_start()
    
    execute_write(
        """
        INSERT INTO user_points (user_id, points, week_start)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET 
            points = points + excluded.points,
            week_start = excluded.week_start
        """,
        (user_id, points, week_start.isoformat())
    )
    
    # پاک کردن کش امتیاز
    CacheManager.invalidate(f"points_{user_id}")
    CacheManager.invalidate("top_users")


def get_user_points(user_id: int) -> int:
    """دریافت امتیاز کاربر"""
    cache_key = f"points_{user_id}"
    cached = CacheManager.get(cache_key)
    if cached is not None:
        return cached
    
    results = execute_query(
        "SELECT points FROM user_points WHERE user_id = ?",
        (user_id,)
    )
    points = results[0][0] if results else 0
    CacheManager.set(cache_key, points, ttl=10)
    return points


def get_top_users(limit: int = 5) -> list:
    """دریافت برترین کاربران"""
    cache_key = "top_users"
    cached = CacheManager.get(cache_key)
    if cached is not None:
        return cached
    
    results = execute_query(
        "SELECT user_id, points FROM user_points ORDER BY points DESC LIMIT ?",
        (limit,)
    )
    
    CacheManager.set(cache_key, results, ttl=30)
    return results


def get_week_start() -> datetime:
    """محاسبه شروع هفته (شنبه)"""
    now = datetime.now()
    days_since_saturday = (now.weekday() + 2) % 7
    start = now - timedelta(days=days_since_saturday)
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def reset_weekly_points() -> list:
    """ریست امتیازهای هفتگی"""
    top_users = get_top_users(5)
    
    if not top_users:
        return []
    
    week_start = get_week_start()
    
    for user_id, points in top_users:
        if points > 0:
            execute_write(
                "INSERT INTO weekly_winners (user_id, points, week_start) VALUES (?, ?, ?)",
                (user_id, points, week_start.isoformat())
            )
    
    # ۳ نفر برتر پاداش می‌گیرند
    for i, (user_id, points) in enumerate(top_users[:3]):
        if points > 0:
            activate_referral_reward(user_id, 3, 'weekly_winner')
    
    # ریست امتیازها
    execute_write("DELETE FROM user_points")
    
    # پاک کردن کش
    CacheManager.invalidate("top_users")
    CacheManager.invalidate("weekly_winners")
    
    return top_users


def get_weekly_winners() -> list:
    """دریافت برندگان هفته گذشته"""
    cache_key = "weekly_winners"
    cached = CacheManager.get(cache_key)
    if cached is not None:
        return cached
    
    results = execute_query(
        "SELECT user_id, points, week_start FROM weekly_winners ORDER BY points DESC LIMIT 5"
    )
    
    CacheManager.set(cache_key, results, ttl=3600)
    return results


def activate_referral_reward(user_id: int, days: int, reward_type: str) -> None:
    """فعال کردن پاداش دعوت برای کاربر"""
    until = datetime.now() + timedelta(days=days)
    execute_write(
        "INSERT OR REPLACE INTO referral_rewards (user_id, reward_active_until, reward_type) VALUES (?, ?, ?)",
        (user_id, until.isoformat(), reward_type)
    )


def has_referral_reward(user_id: int) -> bool:
    """بررسی اینکه کاربر پاداش دعوت فعال دارد"""
    results = execute_query(
        "SELECT 1 FROM referral_rewards WHERE user_id = ? AND reward_active_until > datetime('now')",
        (user_id,)
    )
    return bool(results)


def get_weekly_report() -> dict:
    """دریافت گزارش هفتگی"""
    from database.remix_repo import get_weekly_report as repo_report
    return repo_report()