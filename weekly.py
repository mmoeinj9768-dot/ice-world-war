# jobs/weekly.py
# Jobهای هفتگی

from datetime import time
from telegram.ext import ContextTypes
from services.points_service import reset_weekly_points, get_weekly_winners
from database.remix_repo import get_weekly_report
from database.user_repo import get_user
from utils.logger import get_logger
from config import OWNER_ID

logger = get_logger(__name__)


async def weekly_report(context: ContextTypes.DEFAULT_TYPE):
    """ارسال گزارش هفتگی به مالک"""
    try:
        report = get_weekly_report()
        
        # دریافت برترین‌های این هفته
        from services.points_service import get_top_users
        top_users = get_top_users(3)
        
        msg = (
            f"📊 **گزارش هفتگی ربات**\n\n"
            f"👥 کاربران جدید: {report['new_users']}\n"
            f"📥 دانلودهای جدید: {report['new_downloads']}\n"
            f"📝 درخواست‌های جدید: {report['new_requests']}\n\n"
            f"🏆 **پربازدیدترین ریمیکس‌های هفته:**\n"
        )
        
        if report['top_remixes']:
            for i, (code, title, artist, views) in enumerate(report['top_remixes'], 1):
                msg += f"{i}. `{code}` - {title} - {artist} (👁 {views})\n"
        else:
            msg += "هیچ ریمیکسی موجود نیست\n"
        
        msg += f"\n🏅 **برترین‌های این هفته:**\n"
        if top_users:
            for i, (user_id, points) in enumerate(top_users, 1):
                user = get_user(user_id)
                name = user[2] if user else "کاربر ناشناس"
                msg += f"{i}. {name} — {points} امتیاز\n"
        else:
            msg += "هیچ کاربری امتیازی کسب نکرده است\n"
        
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=msg,
            parse_mode="Markdown"
        )
        logger.info("✅ Weekly report sent to owner")
    except Exception as e:
        logger.error(f"❌ Error sending weekly report: {e}")


async def reset_weekly_points_job(context: ContextTypes.DEFAULT_TYPE):
    """ریست امتیازهای هفتگی و اعطای پاداش"""
    try:
        top_users = reset_weekly_points()
        logger.info(f"✅ Weekly points reset. Top users: {top_users[:3] if top_users else 'none'}")
        
        if top_users:
            msg = "🔄 **امتیازهای هفتگی ریست شد.**\n\n"
            msg += "🏆 **برترین‌های این هفته:**\n"
            
            for i, (user_id, points) in enumerate(top_users[:3], 1):
                user = get_user(user_id)
                name = user[2] if user else "کاربر ناشناس"
                msg += f"{i}. {name} — {points} امتیاز (۳ روز عضویت رایگان)\n"
            
            # ارسال به مالک
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=msg,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"❌ Error resetting weekly points: {e}")


def setup_jobs(job_queue):
    """تنظیم Jobهای هفتگی"""
    if not job_queue:
        logger.warning("⚠️ JobQueue not available! Jobs will not run.")
        return
    
    try:
        # گزارش هفتگی - هر روز ساعت ۹ صبح
        job_queue.run_daily(
            weekly_report,
            time=time(hour=9, minute=0),
            name="weekly_report"
        )
        logger.info("✅ Weekly report job scheduled (09:00 daily)")
        
        # ریست امتیازها - هر روز ساعت ۰۰:۰۰
        job_queue.run_daily(
            reset_weekly_points_job,
            time=time(hour=0, minute=0),
            name="reset_points"
        )
        logger.info("✅ Weekly points reset job scheduled (00:00 daily)")
        
    except Exception as e:
        logger.error(f"❌ Error setting up jobs: {e}")