# core/app.py
# راه‌اندازی و پیکربندی اپلیکیشن

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from config import TOKEN, READ_TIMEOUT, WRITE_TIMEOUT, CONNECT_TIMEOUT, POOL_TIMEOUT
from utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> Application:
    """ایجاد و پیکربندی اپلیکیشن اصلی"""
    
    app = ApplicationBuilder() \
        .token(TOKEN) \
        .read_timeout(READ_TIMEOUT) \
        .write_timeout(WRITE_TIMEOUT) \
        .connect_timeout(CONNECT_TIMEOUT) \
        .pool_timeout(POOL_TIMEOUT) \
        .build()
    
    logger.info("✅ Application created successfully")
    return app


def setup_handlers(app: Application) -> None:
    """ثبت تمام هندلرها"""
    
    from handlers.user import (
        start,
        random_remix,
        top_remixes,
        get_remix_by_code,
        song_request,
        invite_friends,
        help_command,
        handle_unknown,
        handle_channel_leave,
        handle_file_upload
    )
    from handlers.admin import (
        admin_panel,
        admin_remix_panel,
        admin_channel_panel,
        admin_admin_panel,
        admin_settings_panel,
        add_remix,
        delete_remix,
        search_remix,
        remix_stats,
        back_to_main,
        close_panel,
        add_button_command,
        handle_add_remix_audio
    )
    from handlers.callback import callback_handler
    from handlers.group import handle_group_messages
    
    # ===== هندلرهای دستورات =====
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("addbutton", add_button_command))
    
    # ===== هندلرهای کاربران عادی =====
    app.add_handler(MessageHandler(filters.Regex("^ریمیکس تصادفی 🎲$"), random_remix))
    app.add_handler(MessageHandler(filters.Regex("^ریمیکس‌های برتر 🏆$"), top_remixes))
    app.add_handler(MessageHandler(filters.Regex("^دریافت ریمیکس با کد 📥$"), get_remix_by_code))
    app.add_handler(MessageHandler(filters.Regex("^پیشنهاد آهنگ برای ادیت 📤$"), song_request))
    app.add_handler(MessageHandler(filters.Regex("^دعوت دوستان 🎁$"), invite_friends))
    app.add_handler(MessageHandler(filters.Regex("^راهنما ℹ️$"), help_command))
    
    # ===== هندلرهای پنل ادمین =====
    app.add_handler(MessageHandler(filters.Regex("^پنل ریمیکس 🎵$"), admin_remix_panel))
    app.add_handler(MessageHandler(filters.Regex("^پنل عضویت اجباری 🔗$"), admin_channel_panel))
    app.add_handler(MessageHandler(filters.Regex("^پنل ادمین 👥$"), admin_admin_panel))
    app.add_handler(MessageHandler(filters.Regex("^پنل تنظیمات ⚙️$"), admin_settings_panel))
    
    # ===== زیرمجموعه پنل ریمیکس =====
    app.add_handler(MessageHandler(filters.Regex("^افزودن ریمیکس جدید ➕$"), add_remix))
    app.add_handler(MessageHandler(filters.Regex("^حذف ریمیکس 🗑$"), delete_remix))
    app.add_handler(MessageHandler(filters.Regex("^جستجوی ریمیکس با کد 🔍$"), search_remix))
    app.add_handler(MessageHandler(filters.Regex("^آمار ریمیکس 💎$"), remix_stats))
    
    # ===== دکمه‌های عمومی =====
    app.add_handler(MessageHandler(filters.Regex("^بازگشت ↩️$"), back_to_main))
    app.add_handler(MessageHandler(filters.Regex("^بستن پنل ❌$"), close_panel))
    
    # ===== هندلرهای Callback =====
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # ===== هندلرهای گروه خصوصی =====
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT, handle_group_messages))
    
    # ===== هندلرهای فایل =====
    app.add_handler(MessageHandler(filters.AUDIO, handle_file_upload))
    app.add_handler(MessageHandler(filters.PHOTO, handle_file_upload))
    
    # ===== هندلرهای عمومی =====
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_channel_leave))
    
    logger.info("✅ All handlers registered")