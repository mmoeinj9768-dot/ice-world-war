# utils/logger.py
# سیستم لاگ‌گیری

import logging
import sys
from pathlib import Path
from config import LOG_LEVEL, LOG_FILE

# ===== ایجاد پوشه لاگ =====
Path("logs").mkdir(exist_ok=True)


def setup_logger() -> logging.Logger:
    """تنظیمات لاگ‌گیری"""
    
    # تنظیمات اصلی
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"logs/{LOG_FILE}", encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # تنظیمات خاص برای کتابخانه‌های دیگر
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    
    logger = logging.getLogger("bot")
    logger.info("✅ Logger initialized")
    return logger


def get_logger(name: str) -> logging.Logger:
    """دریافت یک Logger با نام مشخص"""
    return logging.getLogger(f"bot.{name}")