# utils/cache.py
# سیستم کش در حافظه

import time
from typing import Any, Optional, Dict
from threading import Lock
from utils.logger import get_logger

logger = get_logger(__name__)

# ===== کش ساده در حافظه =====
_cache: Dict[str, tuple] = {}
_cache_lock = Lock()


class CacheManager:
    """مدیریت کش با TTL"""
    
    @classmethod
    def init(cls):
        """مقداردهی کش"""
        global _cache
        with _cache_lock:
            _cache = {}
            logger.info("✅ Cache initialized")
    
    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """دریافت از کش"""
        with _cache_lock:
            if key in _cache:
                value, expiry = _cache[key]
                if expiry > time.time():
                    return value
                else:
                    del _cache[key]
            return None
    
    @classmethod
    def set(cls, key: str, value: Any, ttl: int = 30):
        """ذخیره در کش"""
        with _cache_lock:
            _cache[key] = (value, time.time() + ttl)
    
    @classmethod
    def invalidate(cls, key: str):
        """پاک کردن یک کلید از کش"""
        with _cache_lock:
            if key in _cache:
                del _cache[key]
                logger.debug(f"Cache invalidated: {key}")
    
    @classmethod
    def invalidate_pattern(cls, pattern: str):
        """پاک کردن کلیدهایی که با الگو شروع می‌شوند"""
        with _cache_lock:
            keys = list(_cache.keys())
            for key in keys:
                if key.startswith(pattern):
                    del _cache[key]
                    logger.debug(f"Cache invalidated: {key}")
    
    @classmethod
    def clear(cls):
        """پاک کردن کل کش"""
        with _cache_lock:
            _cache.clear()
            logger.info("Cache cleared")
    
    @classmethod
    def get_stats(cls) -> dict:
        """دریافت آمار کش"""
        with _cache_lock:
            return {
                "size": len(_cache),
                "keys": list(_cache.keys())[:10]  # فقط ۱۰ کلید اول
            }