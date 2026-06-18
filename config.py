# config.py
# تنظیمات اصلی ربات EDIT 41

import os
from dotenv import load_dotenv

# بارگذاری فایل .env
load_dotenv()

# ============================================================
# توکن‌ها و اطلاعات اصلی
# ============================================================

TOKEN = os.getenv("TOKEN", "")
if not TOKEN:
    raise ValueError("❌ TOKEN not found in .env file!")

OWNER_ID = int(os.getenv("OWNER_ID", 0))
if OWNER_ID == 0:
    raise ValueError("❌ OWNER_ID not found in .env file!")

BOT_USERNAME = os.getenv("BOT_USERNAME", "@EDIT_41_BOT")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@EDIT_41")

# ============================================================
# تنظیمات دیتابیس
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")
DATABASE_NAME = "bot.db"

# ============================================================
# تنظیمات Redis (اختیاری)
# ============================================================

REDIS_URL = os.getenv("REDIS_URL", "")
REDIS_ENABLED = bool(REDIS_URL)

# ============================================================
# تنظیمات کش
# ============================================================

CACHE_TTL_MEMBERSHIP = 60   # 60 ثانیه
CACHE_TTL_FEATURES = 120    # 2 دقیقه
CACHE_TTL_STATS = 30        # 30 ثانیه
CACHE_TTL_POINTS = 10       # 10 ثانیه

# ============================================================
# تنظیمات گروه درخواست‌ها
# ============================================================

REQUEST_GROUP_ID = int(os.getenv("REQUEST_GROUP_ID", -1004434170476))
REQUEST_COOLDOWN_DAYS = int(os.getenv("REQUEST_COOLDOWN_DAYS", 3))

# ============================================================
# تنظیمات امنیتی
# ============================================================

ADMIN_PANEL_PASSWORD = os.getenv("ADMIN_PANEL_PASSWORD", "9729")
RATE_LIMIT_PER_USER = int(os.getenv("RATE_LIMIT_PER_USER", 30))  # درخواست در دقیقه

# ============================================================
# تنظیمات ذخیره‌سازی
# ============================================================

STORAGE_PATH = os.getenv("STORAGE_PATH", "storage")
REMIXES_PATH = os.path.join(STORAGE_PATH, "remixes")
COVERS_PATH = os.path.join(STORAGE_PATH, "covers")

# ============================================================
# تنظیمات لاگ
# ============================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "bot.log")

# ============================================================
# تنظیمات Jobها
# ============================================================

WEEKLY_REPORT_HOUR = int(os.getenv("WEEKLY_REPORT_HOUR", 9))
WEEKLY_REPORT_MINUTE = int(os.getenv("WEEKLY_REPORT_MINUTE", 0))
RESET_POINTS_HOUR = int(os.getenv("RESET_POINTS_HOUR", 0))
RESET_POINTS_MINUTE = int(os.getenv("RESET_POINTS_MINUTE", 0))

# ============================================================
# تنظیمات ربات
# ============================================================

READ_TIMEOUT = int(os.getenv("READ_TIMEOUT", 30))
WRITE_TIMEOUT = int(os.getenv("WRITE_TIMEOUT", 30))
CONNECT_TIMEOUT = int(os.getenv("CONNECT_TIMEOUT", 30))
POOL_TIMEOUT = int(os.getenv("POOL_TIMEOUT", 30))

# ============================================================
# اطلاعات سیستم
# ============================================================

VERSION = "2.0.0"
AUTHOR = "EDIT 41"