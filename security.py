# utils/security.py
# توابع امنیتی

from database.db import execute_query, execute_write
from config import OWNER_ID
from typing import List
from utils.logger import get_logger

logger = get_logger(__name__)


def is_owner(user_id: int) -> bool:
    """بررسی مالک بودن"""
    return user_id == OWNER_ID


def is_admin(user_id: int) -> bool:
    """بررسی ادمین بودن"""
    results = execute_query(
        "SELECT 1 FROM admins WHERE user_id = ?",
        (user_id,)
    )
    return bool(results)


def add_admin(user_id: int, added_by: int) -> bool:
    """افزودن ادمین جدید (فقط مالک)"""
    if not is_owner(added_by):
        logger.warning(f"User {added_by} tried to add admin without permission")
        return False
    
    execute_write(
        "INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?, ?)",
        (user_id, added_by)
    )
    logger.info(f"Admin {user_id} added by {added_by}")
    return True


def remove_admin(user_id: int, removed_by: int) -> bool:
    """حذف ادمین (فقط مالک)"""
    if not is_owner(removed_by):
        logger.warning(f"User {removed_by} tried to remove admin without permission")
        return False
    
    if user_id == OWNER_ID:
        logger.warning(f"User {removed_by} tried to remove owner")
        return False
    
    execute_write("DELETE FROM admins WHERE user_id = ?", (user_id,))
    logger.info(f"Admin {user_id} removed by {removed_by}")
    return True


def get_all_admins() -> List[int]:
    """دریافت لیست ادمین‌ها"""
    results = execute_query("SELECT user_id FROM admins")
    return [r[0] for r in results]


def is_admin_or_owner(user_id: int) -> bool:
    """بررسی ادمین یا مالک بودن"""
    return is_owner(user_id) or is_admin(user_id)