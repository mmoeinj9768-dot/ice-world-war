# database/vote_repo.py
# Repository برای جدول remix_votes

from database.db import execute_query, execute_write, get_connection
from datetime import datetime
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


def get_user_vote(user_id: int, remix_code: int) -> Optional[int]:
    """دریافت رأی کاربر برای یک ریمیکس"""
    results = execute_query(
        "SELECT vote FROM remix_votes WHERE user_id = ? AND remix_code = ?",
        (user_id, remix_code)
    )
    return results[0][0] if results else None


def set_user_vote(user_id: int, remix_code: int, vote: int) -> None:
    """
    ثبت یا تغییر رأی کاربر (Atomic)
    vote: 1 = لایک, -1 = دیسلایک, 0 = حذف رأی
    """
    if vote not in (-1, 0, 1):
        raise ValueError(f"Invalid vote: {vote}")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN IMMEDIATE")
        
        # دریافت رأی قبلی
        cursor.execute(
            "SELECT vote FROM remix_votes WHERE user_id = ? AND remix_code = ?",
            (user_id, remix_code)
        )
        old = cursor.fetchone()
        old_vote = old[0] if old else None
        
        should_add_points = False
        
        if old_vote == vote:
            conn.commit()
            return
        
        if vote == 0:
            # حذف رأی
            cursor.execute(
                "DELETE FROM remix_votes WHERE user_id = ? AND remix_code = ?",
                (user_id, remix_code)
            )
            
            if old_vote == 1:
                cursor.execute(
                    "UPDATE remixes SET likes = CASE WHEN likes > 0 THEN likes - 1 ELSE 0 END WHERE code = ?",
                    (remix_code,)
                )
            elif old_vote == -1:
                cursor.execute(
                    "UPDATE remixes SET dislikes = CASE WHEN dislikes > 0 THEN dislikes - 1 ELSE 0 END WHERE code = ?",
                    (remix_code,)
                )
        elif old_vote is None:
            # رأی جدید
            cursor.execute(
                "INSERT INTO remix_votes (user_id, remix_code, vote) VALUES (?, ?, ?)",
                (user_id, remix_code, vote)
            )
            
            if vote == 1:
                cursor.execute(
                    "UPDATE remixes SET likes = likes + 1 WHERE code = ?",
                    (remix_code,)
                )
                should_add_points = True
            elif vote == -1:
                cursor.execute(
                    "UPDATE remixes SET dislikes = dislikes + 1 WHERE code = ?",
                    (remix_code,)
                )
        else:
            # تغییر رأی
            cursor.execute(
                "UPDATE remix_votes SET vote = ? WHERE user_id = ? AND remix_code = ?",
                (vote, user_id, remix_code)
            )
            
            if old_vote == 1 and vote == -1:
                cursor.execute(
                    "UPDATE remixes SET likes = CASE WHEN likes > 0 THEN likes - 1 ELSE 0 END, dislikes = dislikes + 1 WHERE code = ?",
                    (remix_code,)
                )
            elif old_vote == -1 and vote == 1:
                cursor.execute(
                    "UPDATE remixes SET likes = likes + 1, dislikes = CASE WHEN dislikes > 0 THEN dislikes - 1 ELSE 0 END WHERE code = ?",
                    (remix_code,)
                )
        
        conn.commit()
        
        if should_add_points:
            # اضافه کردن امتیاز برای لایک
            from services.points_service import add_points
            add_points(user_id, 1, "like")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error setting vote: {e}")
        raise
    finally:
        cursor.close()


def rebuild_votes(remix_code: int) -> tuple:
    """بازسازی شمارنده‌های لایک/دیسلایک"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN IMMEDIATE")
        
        cursor.execute(
            "SELECT COUNT(*) FROM remix_votes WHERE remix_code = ? AND vote = 1",
            (remix_code,)
        )
        likes = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT COUNT(*) FROM remix_votes WHERE remix_code = ? AND vote = -1",
            (remix_code,)
        )
        dislikes = cursor.fetchone()[0]
        
        cursor.execute(
            "UPDATE remixes SET likes = ?, dislikes = ? WHERE code = ?",
            (likes, dislikes, remix_code)
        )
        
        conn.commit()
        return likes, dislikes
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error rebuilding votes: {e}")
        raise
    finally:
        cursor.close()