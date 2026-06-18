# handlers/user.py
# هندلرهای کاربران عادی

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.remix_service import *
from services.membership_service import *
from services.points_service import *
from utils.security import *
from utils.cache import CacheManager
from core.middleware import StateMiddleware, rate_limit, log_request
from config import BOT_USERNAME, CHANNEL_USERNAME, REQUEST_COOLDOWN_DAYS, REQUEST_GROUP_ID
from datetime import datetime
import re
from database import get_active_channels
from database.db import save_pending_remix, get_pending_remix, clear_pending_remix


# ============================================================
# کیبورد کاربران عادی
# ============================================================
def create_user_keyboard():
    keyboard = [
        [KeyboardButton("ریمیکس تصادفی 🎲"), KeyboardButton("ریمیکس‌های برتر 🏆")],
        [KeyboardButton("دریافت ریمیکس با کد 📥"), KeyboardButton("پیشنهاد آهنگ برای ادیت 📤")],
        [KeyboardButton("دعوت دوستان 🎁"), KeyboardButton("راهنما ℹ️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def create_membership_keyboard(channels):
    keyboard = []
    for channel_id, channel_link, chat_id, display_name in channels:
        keyboard.append([InlineKeyboardButton(f"عضویت {display_name} 🔰", url=channel_link)])
    keyboard.append([InlineKeyboardButton("عضو شدم ✅", callback_data="check_membership")])
    return InlineKeyboardMarkup(keyboard)


def create_vote_keyboard(remix_code, user_id):
    from database.vote_repo import get_user_vote
    from database.remix_repo import get_remix
    
    remix = get_remix(remix_code)
    if not remix:
        return InlineKeyboardMarkup([])
    
    likes = remix[6] if len(remix) > 6 else 0
    dislikes = remix[7] if len(remix) > 7 else 0
    
    user_vote = get_user_vote(user_id, remix_code)
    
    like_emoji = "👍" if user_vote != 1 else "✅👍"
    dislike_emoji = "👎" if user_vote != -1 else "✅👎"
    
    keyboard = [
        [
            InlineKeyboardButton(f"{like_emoji} {likes}", callback_data=f"vote_{remix_code}_1"),
            InlineKeyboardButton(f"{dislike_emoji} {dislikes}", callback_data=f"vote_{remix_code}_-1")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# ============================================================
# هندلرها
# ============================================================

@log_request
@rate_limit(10)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "کاربر"
    first_name = update.effective_user.first_name or "کاربر"
    
    add_user(user_id, username, first_name)
    args = context.args
    
    # ===== لینک دعوت =====
    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0].split("ref_")[1])
            if referrer_id != user_id:
                from database.remix_repo import add_referral
                add_referral(referrer_id, user_id)
                add_points(referrer_id, 3, "referral")
                await context.bot.send_message(
                    referrer_id,
                    f"🎁 شما یک دوست را به ربات دعوت کردید!\n+۳ امتیاز به حساب شما اضافه شد."
                )
                await update.message.reply_text(
                    f"🎵 به ربات EDIT 41 خوش آمدید!\n\n"
                    f"💠 @{CHANNEL_USERNAME.replace('@', '')}\n"
                    f"بهترین کانال ادیت و ریمیکس‌های رپ\n\n"
                    f"🔥 شما با دعوت دوست خود وارد شدید!\n"
                    f"🎁 {REQUEST_COOLDOWN_DAYS} روز بدون عضویت اجباری ریمیکس دانلود کنید.\n\n"
                    f"📌 برای شروع، روی دکمه‌های زیر کلیک کنید."
                )
                from database.user_repo import activate_referral_reward
                activate_referral_reward(user_id, REQUEST_COOLDOWN_DAYS, 'referred')
                return
        except Exception as e:
            print(f"❌ Error processing referral: {e}")
    
    # ===== لینک ریمیکس =====
    if args and args[0].startswith("code_"):
        try:
            code_str = args[0].split("code_")[1]
            remix_code = int(code_str)
            await handle_remix_request(update, context, remix_code)
            return
        except:
            await update.message.reply_text("لینک نامعتبر است ❌")
            return
    
    # ===== مالک =====
    if is_owner(user_id):
        StateMiddleware.clear(context)
        from handlers.admin import create_admin_main_keyboard
        keyboard = create_admin_main_keyboard()
        await update.message.reply_text(
            f"👑 خوش آمدید مالک عزیز!\n\n{CHANNEL_USERNAME}\n\n🔧 پنل مدیریت\nلطفاً یکی از بخش‌های زیر را انتخاب کنید:",
            reply_markup=keyboard
        )
        return
    
    # ===== کاربر عادی =====
    is_new = not has_user_started(user_id)
    if is_new:
        welcome_text = (
            f"🎵 به ربات EDIT 41 خوش آمدید!\n\n"
            f"💠 {CHANNEL_USERNAME}\n"
            f"بهترین کانال ادیت و ریمیکس‌های رپ\n\n"
            f"🔥 اینجا می‌توانید:\n"
            f"✅ ریمیکس‌های جدید و انحصاری را دریافت کنید\n"
            f"✅ به آهنگ‌ها امتیاز دهید\n"
            f"✅ آهنگ مورد نظر خود را برای ادیت پیشنهاد دهید\n\n"
            f"📌 برای شروع، روی دکمه‌های زیر کلیک کنید\n\n"
            f"💠 {CHANNEL_USERNAME}\n"
            f"🔗 @{BOT_USERNAME.replace('@', '')}"
        )
    else:
        welcome_text = (
            f"🎵 به ربات EDIT 41 خوش آمدید!\n\n"
            f"{CHANNEL_USERNAME}\n"
            f"برای دریافت ریمیکس، روی دکمه‌های زیر کلیک کنید"
        )
    
    keyboard = create_user_keyboard()
    await update.message.reply_text(welcome_text, reply_markup=keyboard)


async def handle_remix_request(update: Update, context: ContextTypes.DEFAULT_TYPE, remix_code: int):
    """پردازش درخواست ریمیکس"""
    user_id = update.effective_user.id
    username = update.effective_user.first_name or "کاربر"
    
    has_reward = has_referral_reward(user_id)
    
    if not has_reward:
        is_member, failed_channel = check_all_memberships(user_id, context.bot)
        if not is_member:
            save_pending_remix(user_id, remix_code)
            channels = get_active_channels()
            keyboard = create_membership_keyboard(channels)
            text = f"🎵 دریافت ریمیکس\n\nکاربر {username} عزیز ❤️\n\nبرای دریافت نسخه کامل ریمیکس، ابتدا در کانال‌های زیر عضو شوید و سپس روی گزینه «عضو شدم ✅» ضربه بزنید\n\nپس از تأیید عضویت، فایل به صورت خودکار ارسال خواهد شد 🎧🔥"
            await update.message.reply_text(text, reply_markup=keyboard)
            return
    
    # ارسال ریمیکس
    remix = get_remix(remix_code)
    if not remix:
        await update.message.reply_text("ریمیکس مورد نظر یافت نشد ❌")
        return
    
    code, file_path, title, artist, cover_path, views, likes, dislikes, created_at = remix
    
    increment_views(code, user_id)
    
    vote_keyboard = create_vote_keyboard(code, user_id)
    caption = f"🎵 {title}\n🎤 خواننده: {artist}\n🎚 کد: {code}\n📅 تاریخ انتشار: {created_at[:10] if created_at else 'نامشخص'}\n\n🎧 از شنیدن این ریمیکس لذت بردید؟ نظرتون رو با کلیک روی دکمه‌های زیر ثبت کنید 👇"
    
    try:
        with open(file_path, 'rb') as audio_file:
            await update.message.reply_audio(
                audio=audio_file,
                title=title,
                performer=artist,
                caption=caption,
                reply_markup=vote_keyboard
            )
    except Exception as e:
        await update.message.reply_text("خطا در ارسال فایل ❌ لطفاً بعداً تلاش کنید")


@log_request
async def random_remix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال ریمیکس تصادفی"""
    if not is_feature_enabled('feature_random_remix'):
        await update.message.reply_text("این قابلیت توسط مدیریت غیرفعال شده است ⛔")
        return
    
    remix = get_random_remix()
    if remix:
        code, title, artist, file_path = remix
        await update.message.reply_text(
            f"ریمیکس تصادفی 🎲\n\n🎵 {title}\n🎤 {artist}\n🎚 کد: {code}\n\n🔗 https://t.me/{BOT_USERNAME.replace('@', '')}?start=code_{code}"
        )
    else:
        await update.message.reply_text("هیچ ریمیکسی در دیتابیس وجود ندارد ❌")


@log_request
async def top_remixes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش ریمیکس‌های برتر"""
    if not is_feature_enabled('feature_top_remixes'):
        await update.message.reply_text("این قابلیت توسط مدیریت غیرفعال شده است ⛔")
        return
    
    top_views = get_top_views(3)
    top_likes = get_top_likes(3)
    
    msg = "ریمیکس‌های برتر 🏆\n\n📊 پربازدیدترین:\n"
    if top_views:
        for i, (code, title, artist, views, likes, dislikes, created_at) in enumerate(top_views, 1):
            msg += f"{i}. {code} - {title} - {artist}\n   👁 {views} بازدید\n"
    else:
        msg += "هیچ ریمیکسی موجود نیست\n"
    
    msg += "\n❤️ محبوب‌ترین:\n"
    if top_likes:
        for i, (code, title, artist, views, likes, dislikes, created_at, score) in enumerate(top_likes, 1):
            msg += f"{i}. {code} - {title} - {artist}\n   👍 {likes} | 👎 {dislikes} | امتیاز: {score}\n"
    else:
        msg += "هیچ ریمیکسی موجود نیست"
    
    await update.message.reply_text(msg)


@log_request
async def get_remix_by_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت ریمیکس با کد"""
    if not is_feature_enabled('feature_get_by_code'):
        await update.message.reply_text("این قابلیت توسط مدیریت غیرفعال شده است ⛔")
        return
    
    StateMiddleware.set_state(context, "user", "waiting_for_code")
    await update.message.reply_text(
        "دریافت ریمیکس با کد 📥\n\n"
        "لطفاً کد عددی ریمیکس مورد نظر را وارد کنید:\n"
        "(مثال: 15)"
    )


@log_request
async def song_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیشنهاد آهنگ برای ادیت"""
    if not is_feature_enabled('feature_song_request'):
        await update.message.reply_text("این قابلیت توسط مدیریت غیرفعال شده است ⛔")
        return
    
    user_id = update.effective_user.id
    
    StateMiddleware.clear(context)
    from database.db import get_last_song_request
    last_request = get_last_song_request(user_id)
    if last_request:
        days_diff = (datetime.now() - datetime.fromisoformat(last_request)).days
        if days_diff < REQUEST_COOLDOWN_DAYS:
            remaining = REQUEST_COOLDOWN_DAYS - days_diff
            await update.message.reply_text(
                f"⏳ شما قبلاً درخواست داده‌اید\n\n{remaining} روز دیگر می‌توانید درخواست جدید بفرستید"
            )
            return
    
    StateMiddleware.set_state(context, "user", "song_request")
    await update.message.reply_text(
        "پیشنهاد آهنگ برای ادیت 📤\n\n"
        "لطفاً فایل MP3 آهنگ مورد نظر خود را ارسال کنید\n\n"
        "📌 نکات:\n"
        "• فقط فایل MP3 قابل قبول است\n"
        f"• هر کاربر هر {REQUEST_COOLDOWN_DAYS} روز یک بار می‌تواند درخواست دهد\n"
        "• آهنگ‌های مناسب برای ادیت انتخاب می‌شوند"
    )


@log_request
async def invite_friends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دعوت دوستان"""
    user_id = update.effective_user.id
    ref_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start=ref_{user_id}"
    points = get_user_points(user_id)
    
    await update.message.reply_text(
        f"دعوت دوستان 🎁\n\n"
        f"🎁 با دعوت دوستان خود به ربات، امتیاز بگیرید!\n\n"
        f"🔹 برای هر دعوت، **۳ امتیاز** دریافت می‌کنید\n"
        f"🔹 امتیاز شما: {points}\n"
        f"🔹 ۳ نفر برتر هر هفته، ۳ روز عضویت رایگان دریافت می‌کنند\n\n"
        f"📤 لینک دعوت اختصاصی شما:\n"
        f"`{ref_link}`\n\n"
        f"👇 این لینک را برای دوستان خود ارسال کنید"
    )


@log_request
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنما"""
    if not is_feature_enabled('feature_help'):
        await update.message.reply_text("این قابلیت توسط مدیریت غیرفعال شده است ⛔")
        return
    
    msg = f"راهنما ℹ️\n\n🎵 دریافت ریمیکس:\nروی لینک زیر هر پست در کانال کلیک کنید\n\n🎲 ریمیکس تصادفی:\nاز منوی اصلی گزینه مربوطه را انتخاب کنید\n\n🏆 ریمیکس‌های برتر:\nمشاهده پربازدیدترین و محبوب‌ترین ریمیکس‌ها\n\n📊 آمار ربات:\nمشاهده آمار کلی ربات\n\n🔗 کانال اصلی:\n{CHANNEL_USERNAME}"
    await update.message.reply_text(msg)


async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیام‌های ناشناخته"""
    await update.message.reply_text(
        "❌ دستور یا گزینه نامعتبر است.\n\n"
        "لطفاً از دکمه‌های منوی اصلی استفاده کنید یا /start را بزنید."
    )


async def handle_channel_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رویداد خروج از کانال"""
    if not update.my_chat_member:
        return
    
    chat = update.my_chat_member.chat
    user = update.my_chat_member.from_user
    new_status = update.my_chat_member.new_chat_member.status
    
    if chat.username and chat.username.lower() == CHANNEL_USERNAME.replace("@", "").lower():
        user_id = user.id
        
        if new_status == "left":
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"اخطار خروج از کانال ⚠️\n\nشما از کانال خارج شدید ‼️\n{CHANNEL_USERNAME}\n\nبرای دریافت ریمیکس‌های بیشتر و استفاده از ربات، عضو کانال شوید ✅"
                )
            except Exception as e:
                print(f"Could not send leave notification: {e}")
        
        elif new_status == "member":
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"خوش برگشتی 🎉\n\n{CHANNEL_USERNAME}\n\nهمیشه منتظر ریمیکس‌های جدید باش 💪\n\n🔗 برای دریافت ریمیکس، روی لینک‌های زیر پست‌ها کلیک کنید"
                )
            except Exception as e:
                print(f"Could not send rejoin notification: {e}")


async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش فایل‌های آپلودی"""
    user_id = update.effective_user.id
    action = StateMiddleware.get_step(context)
    user_action = StateMiddleware.get_step(context)
    
    if update.message.audio:
        print(f"🎵 Audio from {user_id}, action: {action}")
        
        if action == 'add_remix_audio':
            # اینجا هندلر ادمین فایل را پردازش می‌کند
            from handlers.admin import handle_add_remix_audio
            await handle_add_remix_audio(update, context)
            return
        
        elif action == 'song_request':
            # پردازش درخواست آهنگ
            audio = update.message.audio
            file_id = audio.file_id
            file_name = audio.file_name or "unknown.mp3"
            
            from database.db import execute_write
            execute_write(
                "INSERT INTO song_requests (user_id, file_id, file_name) VALUES (?, ?, ?)",
                (user_id, file_id, file_name)
            )
            
            user = update.effective_user
            caption = (
                f"📥 درخواست آهنگ جدید\n\n"
                f"👤 کاربر: {user.first_name}\n"
                f"🆔 آیدی: {user.id}\n"
                f"📛 یوزرنیم: @{user.username if user.username else 'ندارد'}\n"
                f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"📁 نام فایل: {file_name}"
            )
            
            await context.bot.send_audio(
                chat_id=REQUEST_GROUP_ID,
                audio=file_id,
                caption=caption
            )
            await update.message.reply_text(
                "✅ درخواست شما با موفقیت ارسال شد\n\n"
                "آهنگ شما بررسی می‌شود و در صورت مناسب بودن، "
                "با آن ادیت ساخته می‌شود 🔥\n\n"
                "📌 نتیجه درخواست به شما اطلاع داده می‌شود"
            )
            StateMiddleware.clear(context)
            return
        
        else:
            await update.message.reply_text("❌ لطفاً ابتدا از منوی اصلی گزینه مورد نظر را انتخاب کنید.")
            return
    
    if update.message.photo:
        await update.message.reply_text("❌ لطفاً فقط فایل MP3 ارسال کنید.")
        return