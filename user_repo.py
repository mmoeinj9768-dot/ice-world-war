# database/user_repo.py
# Repository برای جدول users

from database.db import execute_query, execute_write
from typing import Optional, Tuple, List


def add_user(user_id: int, username: str, first_name: str) -> None:
    """افزودن کاربر جدید"""
    execute_write(
        "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
        (user_id, username, first_name)
    )


def get_user(user_id: int) -> Optional[Tuple]:
    """دریافت اطلاعات کاربر"""
    results = execute_query(
        "SELECT user_id, username, first_name, joined_at FROM users WHERE user_id = ?",
        (user_id,)
    )
    return results[0] if results else None


def get_all_users() -> List[int]:
    """دریافت همه کاربران"""
    results = execute_query("SELECT user_id FROM users")
    return [r[0] for r in results]


def get_today_users() -> int:
    """دریافت تعداد کاربران امروز"""
    results = execute_query(
        "SELECT COUNT(*) FROM users WHERE DATE(joined_at) = DATE('now')"
    )
    return results[0][0] if results else 0


def get_new_users_week() -> int:
    """دریافت تعداد کاربران جدید در هفته گذشته"""
    results = execute_query(
        "SELECT COUNT(*) FROM users WHERE joined_at > datetime('now', '-7 days')"
    )
    return results[0][0] if results else 0


def has_user_started(user_id: int) -> bool:
    """بررسی اینکه کاربر قبلاً استارت کرده یا نه"""
    results = execute_query(
        "SELECT 1 FROM users WHERE user_id = ?",
        (user_id,)
    )
    return bool(results)


def has_user_received_remix(user_id: int, remix_code: int) -> bool:
    """بررسی اینکه کاربر قبلاً ریمیکس دریافت کرده یا نه"""
    results = execute_query(
        "SELECT 1 FROM user_remixes WHERE user_id = ? AND remix_code = ?",
        (user_id, remix_code)
    )
    return bool(results)


def add_user_remix(user_id: int, remix_code: int) -> None:
    """ثبت دریافت ریمیکس توسط کاربر"""
    execute_write(
        "INSERT OR IGNORE INTO user_remixes (user_id, remix_code) VALUES (?, ?)",
        (user_id, remix_code)
    )


def get_user_referral_code(user_id: int) -> str:
    """دریافت کد دعوت کاربر"""
    return f"REF_{user_id}"


def activate_referral_reward(user_id: int, days: int, reward_type: str) -> None:
    """فعال کردن پاداش دعوت"""
    from datetime import datetime, timedelta
    until = datetime.now() + timedelta(days=days)
    execute_write(
        "INSERT OR REPLACE INTO referral_rewards (user_id, reward_active_until, reward_type) VALUES (?, ?, ?)",
        (user_id, until.isoformat(), reward_type)
    )


def has_referral_reward(user_id: int) -> bool:
    """بررسی پاداش دعوت فعال"""
    results = execute_query(
        "SELECT 1 FROM referral_rewards WHERE user_id = ? AND reward_active_until > datetime('now')",
        (user_id,)
    )
    return bool(results)