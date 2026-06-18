# main.py
# نقطه ورود اصلی ربات EDIT 41

import os
import sys
import asyncio
from pathlib import Path

# اضافه کردن مسیر پروژه به PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from config import TOKEN, OWNER_ID, BOT_USERNAME, CHANNEL_USERNAME
from core.app import create_app, setup_handlers
from database.db import init_db
from utils.logger import setup_logger
from jobs.weekly import setup_jobs
from utils.cache import CacheManager
from utils.file_manager import ensure_directories


def main():
    """راه‌اندازی اصلی ربات"""
    
    # ===== راه‌اندازی لاگ =====
    logger = setup_logger()
    logger.info("🚀 Starting EDIT 41 Bot...")
    
    # ===== ایجاد پوشه‌های مورد نیاز =====
    ensure_directories()
    logger.info("✅ Directories created")
    
    # ===== راه‌اندازی کش =====
    CacheManager.init()
    logger.info("✅ Cache initialized")
    
    # ===== راه‌اندازی دیتابیس =====
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        print(f"❌ Database error: {e}")
        sys.exit(1)
    
    # ===== ایجاد اپلیکیشن =====
    try:
        app = create_app()
        logger.info("✅ Application created")
    except Exception as e:
        logger.error(f"❌ Application creation error: {e}")
        print(f"❌ Application creation error: {e}")
        sys.exit(1)
    
    # ===== ثبت هندلرها =====
    try:
        setup_handlers(app)
        logger.info("✅ Handlers registered")
    except Exception as e:
        logger.error(f"❌ Handler registration error: {e}")
        print(f"❌ Handler registration error: {e}")
        sys.exit(1)
    
    # ===== تنظیم Jobها =====
    if app.job_queue:
        try:
            setup_jobs(app.job_queue)
            logger.info("✅ Jobs scheduled")
        except Exception as e:
            logger.error(f"❌ Job scheduling error: {e}")
            # ادامه می‌دهیم چون Jobها حیاتی نیستند
    else:
        logger.warning("⚠️ JobQueue not available! Jobs will not run.")
    
    # ===== اطلاعات نهایی =====
    print(f"""
    ═══════════════════════════════════════
    ✅ EDIT 41 BOT STARTED SUCCESSFULLY
    ═══════════════════════════════════════
    🤖 Bot: {BOT_USERNAME}
    👤 Owner: {OWNER_ID}
    🔗 Channel: {CHANNEL_USERNAME}
    📊 Database: SQLite
    ═══════════════════════════════════════
    """)
    
    logger.info(f"🤖 Bot {BOT_USERNAME} is running...")
    
    # ===== استارت ربات =====
    try:
        app.run_polling()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()