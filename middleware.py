# core/middleware.py
# Middlewareهای کاربردی

import time
from typing import Optional, Dict, Any
from functools import wraps
from utils.logger import get_logger
from utils.cache import CacheManager
from config import RATE_LIMIT_PER_USER

logger = get_logger(__name__)


class StateMiddleware:
    """مدیریت State کاربران"""
    
    @staticmethod
    def get_state(context) -> Optional[Dict[str, Any]]:
        """دریافت state فعلی کاربر"""
        return context.user_data.get("flow")
    
    @staticmethod
    def set_state(context, flow_type: str, step: str, data: Optional[Dict] = None):
        """تنظیم state جدید"""
        context.user_data["flow"] = {
            "type": flow_type,
            "step": step,
            "data": data or {},
            "timestamp": time.time()
        }
    
    @staticmethod
    def clear(context):
        """پاک کردن state"""
        context.user_data.pop("flow", None)
    
    @staticmethod
    def get_step(context) -> Optional[str]:
        """دریافت step فعلی"""
        flow = context.user_data.get("flow")
        return flow.get("step") if flow else None
    
    @staticmethod
    def get_data(context) -> Dict[str, Any]:
        """دریافت داده‌های state"""
        flow = context.user_data.get("flow")
        return flow.get("data", {}) if flow else {}


class RateLimitMiddleware:
    """محدودیت نرخ درخواست‌ها"""
    
    _user_requests: Dict[int, list] = {}
    
    @classmethod
    async def check_limit(cls, user_id: int, limit: int = RATE_LIMIT_PER_USER) -> bool:
        """بررسی محدودیت درخواست کاربر"""
        now = time.time()
        
        if user_id not in cls._user_requests:
            cls._user_requests[user_id] = []
        
        # پاک کردن درخواست‌های قدیمی (آخرین ۶۰ ثانیه)
        cls._user_requests[user_id] = [
            t for t in cls._user_requests[user_id] if now - t < 60
        ]
        
        if len(cls._user_requests[user_id]) >= limit:
            logger.warning(f"⚠️ Rate limit exceeded for user {user_id}")
            return False
        
        cls._user_requests[user_id].append(now)
        return True
    
    @classmethod
    def clear_user(cls, user_id: int):
        """پاک کردن محدودیت کاربر"""
        cls._user_requests.pop(user_id, None)


class LoggingMiddleware:
    """لاگ‌گیری درخواست‌ها"""
    
    @staticmethod
    async def log_request(update, context):
        """لاگ‌گیری درخواست"""
        user_id = update.effective_user.id if update.effective_user else "unknown"
        text = update.message.text if update.message else "non-text"
        
        logger.info(f"📩 {user_id} -> {text[:50] if text else 'non-text'}")


# ============================================================
# دکوراتورهای کاربردی
# ============================================================

def rate_limit(limit: int = RATE_LIMIT_PER_USER):
    """دکوراتور محدودیت نرخ"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            user_id = update.effective_user.id if update.effective_user else 0
            
            if user_id:
                if not await RateLimitMiddleware.check_limit(user_id, limit):
                    await update.message.reply_text(
                        "⏳ شما بیش از حد مجاز درخواست ارسال کرده‌اید. لطفاً کمی صبر کنید."
                    )
                    return
            
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator


def require_state(step: str):
    """دکوراتور بررسی State"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            current_step = StateMiddleware.get_step(context)
            if current_step != step:
                await update.message.reply_text(
                    "❌ لطفاً ابتدا گزینه مورد نظر را از منوی اصلی انتخاب کنید."
                )
                return
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator


def log_request(func):
    """دکوراتور لاگ‌گیری"""
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        await LoggingMiddleware.log_request(update, context)
        return await func(update, context, *args, **kwargs)
    return wrapper