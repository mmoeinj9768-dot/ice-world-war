# database/channel_repo.py
# Repository برای جدول required_channels

from database.db import execute_query, execute_write
from datetime import datetime, timedelta
from typing import Optional, List, Tuple


def add_channel(channel_link: str, chat_id: Optional[str], display_name: str, days: int) -> bool:
    """افزودن کانال جدید به عضویت اجباری"""
    
    # بررسی تکراری بودن
    existing = execute_query(
        """SELECT id FROM required_channels 
           WHERE (channel_link = ? OR (chat_id IS NOT NULL AND chat_id = ?)) 
           AND is_active = 1 
           AND (expires_at IS NULL OR expires_at > datetime('now'))""",
        (channel_link, chat_id)
    )
    
    if existing:
        return False
    
    expires_at = datetime.now() + timedelta(days=days) if days > 0 else None
    
    execute_write(
        "INSERT INTO required_channels (channel_link, chat_id, display_name, expires_at, is_active, is_permanent) VALUES (?, ?, ?, ?, ?, ?)",
        (channel_link, chat_id, display_name, expires_at.isoformat() if expires_at else None, 1, 0)
    )
    return True


def remove_channel(channel_id: int, is_owner: bool = False) -> bool:
    """حذف کانال از عضویت اجباری"""
    results = execute_query(
        "SELECT is_permanent FROM required_channels WHERE id = ?",
        (channel_id,)
    )
    
    if results and results[0][0] == 1 and not is_owner:
        return False
    
    execute_write("DELETE FROM required_channels WHERE id = ?", (channel_id,))
    return True


def get_active_channels() -> List[Tuple]:
    """دریافت کانال‌های فعال (فرمت: id, channel_link, chat_id, display_name)"""
    return execute_query(
        "SELECT id, channel_link, chat_id, display_name FROM required_channels WHERE is_active = 1 AND (expires_at IS NULL OR expires_at > datetime('now'))"
    )


def deactivate_expired_channels() -> None:
    """غیرفعال کردن کانال‌های منقضی شده"""
    execute_write(
        "UPDATE required_channels SET is_active = 0 WHERE expires_at IS NOT NULL AND expires_at <= datetime('now') AND is_permanent = 0"
    )


def get_all_channels() -> List[Tuple]:
    """دریافت همه کانال‌ها (فرمت کامل)"""
    return execute_query(
        "SELECT id, channel_link, chat_id, display_name, expires_at, is_active, is_permanent FROM required_channels ORDER BY id"
    )