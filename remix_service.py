# services/remix_service.py
# سرویس ریمیکس

from database.remix_repo import (
    add_remix as repo_add_remix,
    get_remix as repo_get_remix,
    delete_remix as repo_delete_remix,
    get_all_remixes as repo_get_all,
    get_top_remixes_by_views,
    get_top_remixes_by_likes,
    get_random_remix as repo_get_random,
    increment_views as repo_increment_views,
    get_total_remix_downloads
)
from database.vote_repo import get_user_vote, set_user_vote
from database.user_repo import has_user_received_remix, add_user_remix
from services.points_service import add_points
from utils.cache import CacheManager
from utils.file_manager import save_remix_file, delete_remix_file
from typing import Optional, Tuple, List
from utils.logger import get_logger

logger = get_logger(__name__)


def add_remix(code: int, file, title: str, artist: str, cover) -> bool:
    """افزودن ریمیکس جدید"""
    try:
        # ذخیره فایل‌ها
        mp3_path = save_remix_file(file, code, "mp3")
        cover_path = save_remix_file(cover, code, "jpg") if cover else None
        
        # ذخیره در دیتابیس
        repo_add_remix(code, mp3_path, title, artist, cover_path)
        
        # پاک کردن کش
        CacheManager.invalidate("remix_list")
        CacheManager.invalidate("remix_stats")
        
        logger.info(f"✅ Remix {code} added successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Error adding remix: {e}")
        return False


def get_remix(code: int) -> Optional[Tuple]:
    """دریافت ریمیکس"""
    return repo_get_remix(code)


def delete_remix(code: int) -> bool:
    """حذف ریمیکس"""
    remix = repo_get_remix(code)
    if not remix:
        return False
    
    # حذف فایل‌ها
    delete_remix_file(remix[1])
    if remix[4]:
        delete_remix_file(remix[4])
    
    # حذف از دیتابیس
    repo_delete_remix(code)
    
    # پاک کردن کش
    CacheManager.invalidate("remix_list")
    CacheManager.invalidate("remix_stats")
    
    logger.info(f"✅ Remix {code} deleted")
    return True


def get_all_remixes() -> List[Tuple]:
    """دریافت همه ریمیکس‌ها"""
    cache_key = "remix_list"
    cached = CacheManager.get(cache_key)
    if cached is not None:
        return cached
    
    result = repo_get_all()
    CacheManager.set(cache_key, result, ttl=30)
    return result


def get_top_views(limit: int = 3) -> List[Tuple]:
    """دریافت پربازدیدترین ریمیکس‌ها"""
    return get_top_remixes_by_views(limit)


def get_top_likes(limit: int = 3) -> List[Tuple]:
    """دریافت پرلایک‌ترین ریمیکس‌ها"""
    return get_top_remixes_by_likes(limit)


def get_random_remix() -> Optional[Tuple]:
    """دریافت یک ریمیکس تصادفی"""
    return repo_get_random()


def increment_views(code: int, user_id: int) -> bool:
    """افزایش بازدید ریمیکس"""
    if has_user_received_remix(user_id, code):
        return False
    
    result = repo_increment_views(code, user_id)
    add_user_remix(user_id, code)
    
    if result:
        CacheManager.invalidate("remix_stats")
    
    return result


def get_stats() -> dict:
    """دریافت آمار ریمیکس‌ها"""
    cache_key = "remix_stats"
    cached = CacheManager.get(cache_key)
    if cached is not None:
        return cached
    
    remixes = repo_get_all()
    total = len(remixes)
    downloads = get_total_remix_downloads()
    views = sum(r[3] for r in remixes) if remixes else 0
    likes = sum(r[4] for r in remixes) if remixes else 0
    dislikes = sum(r[5] for r in remixes) if remixes else 0
    
    result = {
        "total_remixes": total,
        "total_downloads": downloads,
        "total_views": views,
        "total_likes": likes,
        "total_dislikes": dislikes,
    }
    
    CacheManager.set(cache_key, result, ttl=10)
    return result


def get_total_downloads() -> int:
    """دریافت تعداد کل دانلودها"""
    return get_total_remix_downloads()


def vote(user_id: int, remix_code: int, vote_type: int) -> None:
    """ثبت رأی کاربر"""
    set_user_vote(user_id, remix_code, vote_type)
    CacheManager.invalidate(f"remix_{remix_code}_votes")