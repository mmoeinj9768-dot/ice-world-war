# handlers/admin.py
# هندلرهای پنل ادمین

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from services.remix_service import *
from services.points_service import *
from database.channel_repo import get_all_channels, get_active_channels, add_channel, remove_channel
from database.user_repo import get_today_users, get_all_users
from utils.security import is_admin_or_owner, is_owner, add_admin, remove_admin, get_all_admins
from utils.cache import CacheManager
from core.middleware import StateMiddleware, rate_limit, log_request
from config import ADMIN_PANEL_PASSWORD, DATABASE_NAME, CHANNEL_USERNAME, BOT_USERNAME
from database.db import backup_database, get_setting, set_setting
from database.db import get_feature_status, set_feature_status, get_all_features
import re
import os


# ============================================================
# کیبوردهای پنل ادمین
# ============================================================

def create_admin_main_keyboard():
    keyboard = [
        [KeyboardButton("پنل ریمیکس 🎵"), KeyboardButton("پنل عضویت اجباری 🔗")],
        [KeyboardButton("پنل ادمین 👥"), KeyboardButton("پنل تنظیمات ⚙️")],
        [KeyboardButton("بستن پنل ❌")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_remix_panel_keyboard():
    keyboard = [
        [KeyboardButton("افزودن ریمیکس جدید ➕"), KeyboardButton("آمار ریمیکس 💎")],
        [KeyboardButton("حذف ریمیکس 🗑"), KeyboardButton("جستجوی ریمیکس با کد 🔍")],
        [KeyboardButton("بازگشت ↩️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_channel_panel_keyboard():
    keyboard = [
        [KeyboardButton("افزودن کانال عضویت ➕"), KeyboardButton("حذف کانال عضویت 🗑")],
        [KeyboardButton("لیست کانال‌های عضویت 📋")],
        [KeyboardButton("بازگشت ↩️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_admin_management_keyboard():
    keyboard = [
        [KeyboardButton("افزودن ادمین ➕"), KeyboardButton("حذف ادمین 🗑")],
        [KeyboardButton("لیست ادمین‌ها 📋")],
        [KeyboardButton("بازگشت ↩️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_settings_panel_keyboard():
    keyboard = [
        [KeyboardButton("وضعیت قابلیت‌ها ⚙️"), KeyboardButton("آمار کاربران 👥")],
        [KeyboardButton("آمار کامل 📊"), KeyboardButton("بکاپ دیتابیس 💾")],
        [KeyboardButton("بازگشت ↩️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_feature_status_keyboard():
    keyboard = [
        [KeyboardButton("خاموش کردن قابلیت 🛑")],
        [KeyboardButton("روشن کردن قابلیت ✅")],
        [KeyboardButton("بازگشت ↩️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ============================================================
# هندلرها
# ============================================================

@log_request
@rate_limit(5)
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ورود به پنل ادمین"""
    user_id = update.effective_user.id
    
    if not is_admin_or_owner(user_id):
        await update.message.reply_text("⛔ شما دسترسی به پنل ادمین ندارید!")
        return
    
    StateMiddleware.clear(context)
    keyboard = create_admin_main_keyboard()
    await update.message.reply_text(
        "🔧 پنل مدیریت\n\nلطفاً یکی از بخش‌های زیر را انتخاب کنید:",
        reply_markup=keyboard
    )


@log_request
async def admin_remix_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پنل ریمیکس"""
    StateMiddleware.clear(context)
    keyboard = create_remix_panel_keyboard()
    await update.message.reply_text("🎵 پنل ریمیکس\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=keyboard)


@log_request
async def admin_channel_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پنل عضویت اجباری"""
    StateMiddleware.clear(context)
    keyboard = create_channel_panel_keyboard()
    await update.message.reply_text("🔗 پنل عضویت اجباری\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=keyboard)


@log_request
async def admin_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پنل مدیریت ادمین‌ها"""
    StateMiddleware.clear(context)
    keyboard = create_admin_management_keyboard()
    await update.message.reply_text("👥 پنل ادمین\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=keyboard)


@log_request
async def admin_settings_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پنل تنظیمات"""
    StateMiddleware.clear(context)
    keyboard = create_settings_panel_keyboard()
    await update.message.reply_text("⚙️ پنل تنظیمات\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=keyboard)


@log_request
async def add_remix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """افزودن ریمیکس جدید"""
    StateMiddleware.set_state(context, "admin", "add_remix_code")
    await update.message.reply_text("📀 افزودن ریمیکس جدید\n\nلطفاً کد عددی ریمیکس را ارسال کنید:\n(مثال: 15)")


@log_request
async def delete_remix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف ریمیکس"""
    StateMiddleware.set_state(context, "admin", "delete_remix")
    await update.message.reply_text("🗑 حذف ریمیکس\n\nلطفاً کد ریمیکس مورد نظر را وارد کنید:")


@log_request
async def search_remix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """جستجوی ریمیکس"""
    StateMiddleware.set_state(context, "admin", "search_remix")
    await update.message.reply_text("🔍 جستجوی ریمیکس\n\nلطفاً کد ریمیکس مورد نظر را وارد کنید:")


@log_request
async def remix_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """آمار ریمیکس‌ها"""
    stats = get_stats()
    remixes = get_all_remixes()
    
    msg = f"آمار ریمیکس 💎\n\n"
    msg += f"🎵 کل ریمیکس‌ها: {stats['total_remixes']}\n"
    msg += f"📥 کل دانلودها: {stats['total_downloads']}\n"
    msg += f"👁 کل بازدیدها: {stats['total_views']}\n\n"
    msg += f"📊 آمار کلی رأی‌ها:\n"
    msg += f"👍 کل لایک‌ها: {stats['total_likes']}\n"
    msg += f"👎 کل دیسلایک‌ها: {stats['total_dislikes']}\n\n"
    
    if stats['total_likes'] + stats['total_dislikes'] > 0:
        rate = (stats['total_likes'] / (stats['total_likes'] + stats['total_dislikes'])) * 100
        msg += f"📈 نرخ محبوبیت: {rate:.1f}% لایک"
    else:
        msg += "📈 هنوز رأیی ثبت نشده"
    
    await update.message.reply_text(msg)


@log_request
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازگشت به منوی اصلی"""
    StateMiddleware.clear(context)
    keyboard = create_admin_main_keyboard()
    await update.message.reply_text("↩️ بازگشت به منوی اصلی", reply_markup=keyboard)


@log_request
async def close_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بستن پنل"""
    StateMiddleware.clear(context)
    from handlers.user import create_user_keyboard
    keyboard = create_user_keyboard()
    await update.message.reply_text("✅ پنل مدیریت بسته شد", reply_markup=keyboard)


@log_request
@rate_limit(5)
async def add_button_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /addbutton"""
    user_id = update.effective_user.id
    
    if not is_admin_or_owner(user_id):
        await update.message.reply_text("شما دسترسی به این دستور ندارید ⛔")
        return
    
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text(
            "نحوه استفاده 🔗\n/addbutton [کد ریمیکس] [لینک پست]\n\nمثال:\n/addbutton 15 https://t.me/EDIT_41/123"
        )
        return
    
    try:
        code = int(args[0])
        link = args[1]
        
        if not (link.startswith("https://t.me/") or link.startswith("t.me/")):
            await update.message.reply_text("لینک معتبر نیست ❌")
            return
        
        if CHANNEL_USERNAME.replace("@", "") not in link:
            await update.message.reply_text(f"لینک باید مربوط به کانال {CHANNEL_USERNAME} باشد ❌")
            return
        
        remix = get_remix(code)
        if not remix:
            await update.message.reply_text(f"ریمیکس با کد {code} یافت نشد ❌")
            return
        
        match = re.search(r'/(\d+)$', link)
        if not match:
            await update.message.reply_text("لینک معتبر نیست ❌ فرمت صحیح: https://t.me/EDIT_41/123")
            return
        
        message_id = int(match.group(1))
        chat_id = f"@{CHANNEL_USERNAME.replace('@', '')}"
        
        button_text = "دریافت ریمیکس کامل 🎵"
        button_url = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start=code_{code}"
        
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(button_text, url=button_url)]])
        
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard
            )
            await update.message.reply_text(
                f"دکمه با موفقیت اضافه شد ✅\n\n🔗 پست: {link}\n🎚 کد ریمیکس: {code}\n\n🔗 لینک دکمه: {button_url}"
            )
        except Exception as e:
            if "Message is not modified" in str(e):
                await update.message.reply_text(
                    f"ℹ️ دکمه قبلاً زیر این پست اضافه شده بود.\n\n"
                    f"🎚 کد: {code}\n"
                    f"🔗 پست: {link}"
                )
            else:
                await update.message.reply_text(f"خطا در افزودن دکمه ❌ {e}\n\nمطمئن شوید ربات در کانال ادمین است و دسترسی ویرایش پیام دارد")
        
    except ValueError:
        await update.message.reply_text("کد ریمیکس باید یک عدد باشد ❌")
    except Exception as e:
        await update.message.reply_text(f"خطا ❌ {e}")


async def handle_add_remix_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = context.user_data.get('new_remix_code')
    
    if not code:
        await update.message.reply_text("❌ کد ریمیکس پیدا نشد. لطفاً مراحل را از اول تکرار کنید.")
        StateMiddleware.clear(context)
        return
    
    try:
        audio = update.message.audio
        if not audio:
            await update.message.reply_text("❌ لطفاً یک فایل MP3 معتبر ارسال کنید.")
            return
        
        audio_file = await audio.get_file()
        mp3_path = f"storage/remixes/remix_{code}.mp3"
        os.makedirs("storage/remixes", exist_ok=True)
        await audio_file.download_to_drive(mp3_path)
        
        # ذخیره در دیتابیس با اطلاعات پیش‌فرض
        success = add_remix(code, None, f"Remix {code}", "Unknown", None)
        
        # فایل را به صورت دستی ذخیره می‌کنیم
        import shutil
        # (در اینجا فایل قبلاً ذخیره شده)
        
        await update.message.reply_text(
            f"✅ ریمیکس با موفقیت ذخیره شد!\n\n"
            f"🎚 کد: {code}\n"
            f"📁 مسیر: {mp3_path}\n\n"
            f"🔗 لینک دریافت:\n"
            f"https://t.me/{BOT_USERNAME.replace('@', '')}?start=code_{code}"
        )
        
    except Exception as e:
        logger.error(f"❌ Error adding remix: {e}")
        await update.message.reply_text(f"❌ خطا در افزودن ریمیکس: {e}")
    finally:
        StateMiddleware.clear(context)