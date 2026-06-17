# bot.py
# کد اصلی ربات EDIT 41

import os
import logging
import shutil
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import TOKEN, OWNER_ID, CHANNEL_USERNAME, BOT_USERNAME, ADMIN_PANEL_PASSWORD, DATABASE_NAME, REQUEST_GROUP_ID, REQUEST_COOLDOWN_DAYS
from database import *
from utils import *

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

user_temp_data = {}
admin_session = {}

# ============================================================
# تابع کمکی برای پاک کردن وضعیت کاربر
# ============================================================
def clear_user_state(context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن تمام حالت‌های قبلی کاربر"""
    context.user_data.pop('admin_action', None)
    context.user_data.pop('user_action', None)
    context.user_data.pop('new_remix_code', None)
    context.user_data.pop('new_remix_title', None)
    context.user_data.pop('new_remix_artist', None)
    context.user_data.pop('new_remix_cover', None)
    context.user_data.pop('new_channel_link', None)
    context.user_data.pop('new_channel_name', None)
    context.user_data.pop('pending_button_link', None)

# ============================================================
# تابع start
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "کاربر"
    first_name = update.effective_user.first_name or "کاربر"

    add_user(user_id, username, first_name)
    args = context.args
    
    # ===== لاگ برای عیب‌یابی =====
    logger.info(f"📩 Start from user {user_id}, args: {args}")

    # ===== بررسی لینک‌های deep link =====
    if args and args[0].startswith("code_"):
        try:
            # استخراج کد از args[0]
            code_str = args[0].split("code_")[1]
            remix_code = int(code_str)
            logger.info(f"✅ Code extracted: {remix_code}")
            context.user_data['pending_remix'] = remix_code
            await check_and_send_remix(update, context, remix_code)
            return
        except ValueError as e:
            logger.error(f"❌ ValueError extracting code from '{args[0]}': {e}")
            await update.message.reply_text("لینک نامعتبر است ❌\nفرمت صحیح: https://t.me/EDIT_41_BOT?start=code_1")
            return
        except Exception as e:
            logger.error(f"❌ Error extracting code: {e}")
            await update.message.reply_text("لینک نامعتبر است ❌")
            return

    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0].split("ref_")[1])
            if referrer_id != user_id:
                add_referral(referrer_id, user_id)
                if check_and_activate_referral_rewards(referrer_id):
                    await context.bot.send_message(
                        referrer_id,
                        f"تبریک 🎉 شما ۵ نفر را به ربات دعوت کردید\nپاداش شما فعال شد ✅\nبه مدت ۱۰ روز بدون عضویت اجباری ریمیکس دانلود کنید 🎵"
                    )
                activate_referral_reward(user_id, 3, 'referred')
                await update.message.reply_text(
                    f"خوش آمدید 🎉\nپاداش شما فعال شد ✅\nبه مدت ۳ روز بدون عضویت اجباری ریمیکس دانلود کنید 🎵"
                )
        except Exception as e:
            logger.error(f"❌ Error processing referral: {e}")

    # ===== اگر کاربر مالک است =====
    if user_id == OWNER_ID:
        keyboard = create_owner_keyboard()
        await update.message.reply_text(
            f"خوش آمدید مالک عزیز 👑\n\n{CHANNEL_USERNAME}\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید",
            reply_markup=keyboard
        )
        return

    # ===== پیام خوش‌آمدگویی برای کاربران عادی =====
    welcome_text = f"به ربات EDIT 41 خوش آمدید 🎵\n\n{CHANNEL_USERNAME}\nبهترین کانال ادیت و ریمیکس‌های فوق‌العاده\n\nبرای دریافت ریمیکس، روی دکمه‌های زیر کلیک کنید"
    keyboard = create_user_keyboard()
    await update.message.reply_text(welcome_text, reply_markup=keyboard)


# ============================================================
# تابع بررسی و ارسال ریمیکس
# ============================================================
async def check_and_send_remix(update: Update, context: ContextTypes.DEFAULT_TYPE, remix_code):
    user_id = update.effective_user.id
    username = update.effective_user.first_name or "کاربر"

    logger.info(f"🔍 check_and_send_remix called for user {user_id}, code {remix_code}")

    deactivate_expired_channels()
    has_reward = has_referral_reward(user_id)
    channels = get_active_channels()

    if not has_reward:
        is_member, failed_channel = check_all_memberships(user_id, channels, context.bot)
        if not is_member:
            context.user_data['pending_remix'] = remix_code
            keyboard = create_membership_keyboard(channels)
            text = f"دریافت ریمیکس 🎵\n\nکاربر {username} عزیز ❤️\n\nبرای دریافت نسخه کامل ریمیکس، ابتدا در کانال‌های زیر عضو شوید و سپس روی گزینه «عضو شدم ✅» ضربه بزنید\n\nپس از تأیید عضویت، فایل به صورت خودکار ارسال خواهد شد 🎧🔥"
            await update.message.reply_text(text, reply_markup=keyboard)
            return

    remix = get_remix(remix_code)
    if not remix:
        logger.error(f"❌ Remix {remix_code} not found in database")
        await update.message.reply_text("ریمیکس مورد نظر یافت نشد ❌")
        return

    code, file_path, title, artist, cover_path, views, likes, dislikes, created_at = remix
    increment_views(code, user_id)
    add_user_remix(user_id, code)

    vote_keyboard = create_vote_keyboard(code, user_id)
    caption = f"🎵 {title}\n🎤 خواننده: {artist}\n🎚 کد: {code}\n📅 تاریخ انتشار: {created_at[:10] if created_at else 'نامشخص'}\n\nاز شنیدن این ریمیکس لذت بردید؟ نظرتون رو با کلیک روی دکمه‌های زیر ثبت کنید 👇"

    try:
        with open(file_path, 'rb') as audio_file:
            await update.message.reply_audio(
                audio=audio_file,
                title=title,
                performer=artist,
                caption=caption,
                reply_markup=vote_keyboard
            )
        logger.info(f"✅ Remix {code} sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending remix: {e}")
        await update.message.reply_text("خطا در ارسال فایل ❌ لطفاً بعداً تلاش کنید")


# ============================================================
# تابع Callback Handler
# ============================================================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    logger.info(f"📩 Callback received: {data} from {user_id}")

    if data == "check_membership":
        remix_code = context.user_data.get('pending_remix')
        if not remix_code:
            await query.edit_message_text("خطا ❌ لطفاً دوباره از لینک وارد شوید")
            return

        deactivate_expired_channels()
        channels = get_active_channels()
        has_reward = has_referral_reward(user_id)

        is_member = True
        if not has_reward:
            for channel_id, channel_link, display_name in channels:
                if not check_user_in_channel(user_id, channel_link, context.bot):
                    is_member = False
                    break

        if not is_member:
            await query.answer("در همه کانال‌ها عضو نشده‌اید ❌", show_alert=True)
            keyboard = create_membership_keyboard(channels)
            await query.edit_message_reply_markup(reply_markup=keyboard)
            return

        await query.edit_message_text("عضویت شما تأیید شد ✅ در حال ارسال فایل...")

        remix = get_remix(remix_code)
        if remix:
            code, file_path, title, artist, cover_path, views, likes, dislikes, created_at = remix
            increment_views(code, user_id)
            add_user_remix(user_id, code)

            vote_keyboard = create_vote_keyboard(code, user_id)
            caption = f"🎵 {title}\n🎤 خواننده: {artist}\n🎚 کد: {code}\n📅 تاریخ انتشار: {created_at[:10] if created_at else 'نامشخص'}\n\nاز شنیدن این ریمیکس لذت بردید؟ نظرتون رو با کلیک روی دکمه‌های زیر ثبت کنید 👇"
            
            try:
                with open(file_path, 'rb') as audio_file:
                    await context.bot.send_audio(
                        chat_id=user_id,
                        audio=audio_file,
                        title=title,
                        performer=artist,
                        caption=caption,
                        reply_markup=vote_keyboard
                    )
                logger.info(f"✅ Remix {code} sent to user {user_id} via callback")
            except Exception as e:
                logger.error(f"Error sending remix via callback: {e}")
                await context.bot.send_message(user_id, "خطا در ارسال فایل ❌")
        else:
            await context.bot.send_message(user_id, "ریمیکس یافت نشد ❌")
            logger.error(f"❌ Remix {remix_code} not found in callback")

        context.user_data.pop('pending_remix', None)
        return

    if data.startswith("vote_"):
        parts = data.split("_")
        remix_code = int(parts[1])
        vote = int(parts[2])

        existing_vote = get_user_vote(user_id, remix_code)
        if existing_vote != 0:
            await query.answer("شما قبلاً به این ریمیکس رأی داده‌اید ⛔", show_alert=True)
            return

        set_user_vote(user_id, remix_code, vote)
        new_keyboard = create_vote_keyboard(remix_code, user_id)
        await query.edit_message_reply_markup(reply_markup=new_keyboard)

        if vote == 1:
            await query.answer("نظر شما ثبت شد 👍 ممنون", show_alert=False)
        else:
            await query.answer("نظر شما ثبت شد 👎 ممنون", show_alert=False)
        return


# ============================================================
# تابع مدیریت پیام‌ها
# ============================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # ===== تشخیص دکمه‌های مالک =====
    if user_id == OWNER_ID:
        if text == "ورود به پنل مالک 👑":
            clear_user_state(context)
            admin_session[user_id] = {'verified': True}
            keyboard = create_admin_main_keyboard()
            await update.message.reply_text(
                "پنل مدیریت 🔧\n\nلطفاً یکی از بخش‌های زیر را انتخاب کنید",
                reply_markup=keyboard
            )
            return

        if text == "ورود به پنل کاربر عادی 👤":
            clear_user_state(context)
            keyboard = create_user_keyboard()
            await update.message.reply_text(
                f"به ربات EDIT 41 خوش آمدید 🎵\n\n{CHANNEL_USERNAME}\nبهترین کانال ادیت و ریمیکس‌های فوق‌العاده\n\nبرای دریافت ریمیکس، روی دکمه‌های زیر کلیک کنید",
                reply_markup=keyboard
            )
            return

    # ===== تشخیص دکمه‌های کاربران عادی =====
    if text == "ریمیکس تصادفی 🎲":
        remix = get_random_remix()
        if remix:
            code, title, artist, file_path = remix
            await update.message.reply_text(
                f"ریمیکس تصادفی 🎲\n\n🎵 {title}\n🎤 {artist}\n🎚 کد: {code}\n\n🔗 {create_remix_link(code)}"
            )
        else:
            await update.message.reply_text("هیچ ریمیکسی در دیتابیس وجود ندارد ❌")
        return

    if text == "ریمیکس‌های برتر 🏆":
        top_views = get_top_remixes_by_views(3)
        top_likes = get_top_remixes_by_likes(3)

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
        return

    if text == "آمار ربات 📊":
        stats = get_stats()
        msg = f"آمار ربات 📊\n\n👥 کل کاربران: {stats['total_users']}\n🎵 کل ریمیکس‌ها: {stats['total_remixes']}\n📥 کل دانلودها: {stats['total_downloads']}\n🔗 کانال‌های فعال: {stats['active_channels']}\n\n🏆 پربازدیدترین:\n"
        if stats['most_viewed']:
            code, title, artist, views = stats['most_viewed']
            msg += f"{code} - {title} - {artist} (👁 {views})"
        else:
            msg += "هیچ ریمیکسی موجود نیست"
        
        msg += "\n\n❤️ محبوب‌ترین:\n"
        if stats['most_liked']:
            code, title, artist, score = stats['most_liked']
            msg += f"{code} - {title} - {artist} (⭐ {score})"
        else:
            msg += "هیچ ریمیکسی موجود نیست"
        
        await update.message.reply_text(msg)
        return

    if text == "راهنما ℹ️":
        msg = f"راهنما ℹ️\n\n🎵 دریافت ریمیکس:\nروی لینک زیر هر پست در کانال کلیک کنید\n\n🎲 ریمیکس تصادفی:\nاز منوی اصلی گزینه مربوطه را انتخاب کنید\n\n🏆 ریمیکس‌های برتر:\nمشاهده پربازدیدترین و محبوب‌ترین ریمیکس‌ها\n\n📊 آمار ربات:\nمشاهده آمار کلی ربات\n\n🔗 کانال اصلی:\n{CHANNEL_USERNAME}"
        await update.message.reply_text(msg)
        return

    if text == "دریافت ریمیکس با کد 📥":
        clear_user_state(context)
        context.user_data['user_action'] = 'get_remix_by_code'
        await update.message.reply_text(
            "دریافت ریمیکس با کد 📥\n\n"
            "لطفاً کد عددی ریمیکس مورد نظر را وارد کنید:\n"
            "(مثال: 15)"
        )
        return

    if text == "پیشنهاد آهنگ برای ادیت 📤":
        clear_user_state(context)
        last_request = get_last_song_request(user_id)
        if last_request:
            days_diff = (datetime.now() - datetime.fromisoformat(last_request)).days
            if days_diff < REQUEST_COOLDOWN_DAYS:
                remaining = REQUEST_COOLDOWN_DAYS - days_diff
                await update.message.reply_text(
                    f"⏳ شما قبلاً درخواست داده‌اید\n\n{remaining} روز دیگر می‌توانید درخواست جدید بفرستید"
                )
                return
        
        context.user_data['user_action'] = 'song_request'
        await update.message.reply_text(
            "پیشنهاد آهنگ برای ادیت 📤\n\n"
            "لطفاً فایل MP3 آهنگ مورد نظر خود را ارسال کنید\n\n"
            "📌 نکات:\n"
            "• فقط فایل MP3 قابل قبول است\n"
            f"• هر کاربر هر {REQUEST_COOLDOWN_DAYS} روز یک بار می‌تواند درخواست دهد\n"
            "• آهنگ‌های مناسب برای ادیت انتخاب می‌شوند"
        )
        return

    # ===== تشخیص دکمه‌های پنل ادمین =====
    if not (user_id == OWNER_ID or is_admin(user_id)):
        return

    # ===== منوی اصلی پنل =====
    if text == "پنل ریمیکس 🎵":
        clear_user_state(context)
        keyboard = create_remix_panel_keyboard()
        await update.message.reply_text(
            "پنل ریمیکس 🎵\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید",
            reply_markup=keyboard
        )
        return

    if text == "پنل عضویت اجباری 🔗":
        clear_user_state(context)
        keyboard = create_channel_panel_keyboard()
        await update.message.reply_text(
            "پنل عضویت اجباری 🔗\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید",
            reply_markup=keyboard
        )
        return

    if text == "پنل ادمین 👥":
        clear_user_state(context)
        keyboard = create_admin_management_keyboard()
        await update.message.reply_text(
            "پنل ادمین 👥\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید",
            reply_markup=keyboard
        )
        return

    if text == "پنل تنظیمات ⚙️":
        clear_user_state(context)
        keyboard = create_settings_panel_keyboard()
        await update.message.reply_text(
            "پنل تنظیمات ⚙️\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید",
            reply_markup=keyboard
        )
        return

    if text == "بستن پنل ❌":
        clear_user_state(context)
        keyboard = create_owner_keyboard()
        await update.message.reply_text(
            "پنل مدیریت بسته شد ✅",
            reply_markup=keyboard
        )
        return

    if text == "بازگشت ↩️":
        clear_user_state(context)
        keyboard = create_admin_main_keyboard()
        await update.message.reply_text(
            "بازگشت به منوی اصلی ↩️",
            reply_markup=keyboard
        )
        return

    # ===== زیرمجموعه پنل ریمیکس =====
    if text == "افزودن ریمیکس جدید ➕":
        clear_user_state(context)
        context.user_data['admin_action'] = 'add_remix_code'
        await update.message.reply_text("افزودن ریمیکس جدید 📀\n\nلطفاً کد عددی ریمیکس را ارسال کنید\n(مثال: 15)")
        return

    if text == "حذف ریمیکس 🗑":
        clear_user_state(context)
        context.user_data['admin_action'] = 'delete_remix'
        await update.message.reply_text("حذف ریمیکس 🗑\n\nلطفاً کد ریمیکس مورد نظر را وارد کنید")
        return

    # ===== زیرمجموعه پنل عضویت =====
    if text == "افزودن کانال عضویت ➕":
        clear_user_state(context)
        context.user_data['admin_action'] = 'add_channel_link'
        await update.message.reply_text("افزودن کانال عضویت 🔗\n\nلطفاً لینک کانال را ارسال کنید\n(مثال: https://t.me/EDIT_41)")
        return

    if text == "حذف کانال عضویت 🗑":
        clear_user_state(context)
        context.user_data['admin_action'] = 'remove_channel'
        channels = get_all_channels()
        if not channels:
            await update.message.reply_text("هیچ کانالی در دیتابیس وجود ندارد 📺")
            return

        msg = "حذف کانال عضویت 🗑\n\nلطفاً آیدی عددی کانال را ارسال کنید\n\n"
        for ch_id, link, name, expires, active, permanent in channels:
            status = "✅" if active else "❌"
            permanent_mark = "⭐ " if permanent else ""
            msg += f"🆔 {ch_id} - {permanent_mark}{name} {status}\n"
        
        await update.message.reply_text(msg)
        return

    if text == "لیست کانال‌های عضویت 📋":
        clear_user_state(context)
        channels = get_all_channels()
        if not channels:
            await update.message.reply_text("هیچ کانالی در دیتابیس وجود ندارد 📺")
            return

        msg = "لیست کانال‌های عضویت 📋\n\n"
        for ch_id, link, name, expires, active, permanent in channels:
            status = "فعال ✅" if active else "غیرفعال ❌"
            permanent_mark = "⭐ دائمی " if permanent else ""
            expiry = expires if expires else "نامحدود"
            msg += f"🆔 {ch_id}\n🔹 {permanent_mark}{name}\n🔗 {link}\n📅 انقضا: {expiry}\n📊 وضعیت: {status}\n\n"

        await update.message.reply_text(msg)
        return

    # ===== زیرمجموعه پنل ادمین =====
    if text == "افزودن ادمین ➕":
        clear_user_state(context)
        context.user_data['admin_action'] = 'add_admin'
        await update.message.reply_text("افزودن ادمین 👥\n\nلطفاً آیدی عددی کاربر جدید را ارسال کنید\n(از @userinfobot بگیرید)")
        return

    if text == "حذف ادمین 🗑":
        clear_user_state(context)
        context.user_data['admin_action'] = 'remove_admin'
        admins = get_all_admins()
        if not admins:
            await update.message.reply_text("هیچ ادمینی غیر از مالک وجود ندارد 👥")
            return

        msg = "حذف ادمین 🗑\n\nلیست ادمین‌های فعلی:\n\n"
        for admin_id in admins:
            msg += f"🆔 {admin_id}\n"
        msg += "\nلطفاً آیدی عددی ادمین مورد نظر را ارسال کنید"
        await update.message.reply_text(msg)
        return

    if text == "لیست ادمین‌ها 📋":
        clear_user_state(context)
        admins = get_all_admins()
        if not admins:
            await update.message.reply_text("هیچ ادمینی غیر از مالک وجود ندارد 👥")
            return

        msg = "لیست ادمین‌ها 📋\n\n"
        for admin_id in admins:
            msg += f"🆔 {admin_id}\n"
        await update.message.reply_text(msg)
        return

    # ===== زیرمجموعه پنل تنظیمات =====
    if text == "تنظیم نرخ تبلیغات 💰":
        clear_user_state(context)
        context.user_data['admin_action'] = 'set_price'
        current_price = get_setting('ad_price_per_day') or "50000"
        await update.message.reply_text(f"تنظیم نرخ تبلیغات 💰\n\nنرخ فعلی: {current_price} تومان در روز\n\nلطفاً نرخ جدید را به تومان وارد کنید\n(مثال: 75000)")
        return

    if text == "تغییر رمز پنل 🔐":
        clear_user_state(context)
        context.user_data['admin_action'] = 'change_password'
        await update.message.reply_text(f"تغییر رمز پنل 🔐\n\nرمز فعلی: {ADMIN_PANEL_PASSWORD}\n\nلطفاً رمز جدید (۴ رقمی) را وارد کنید")
        return

    if text == "آمار کامل 📊":
        clear_user_state(context)
        stats = get_stats()
        msg = f"آمار کامل 📊\n\n👥 کل کاربران: {stats['total_users']}\n🎵 کل ریمیکس‌ها: {stats['total_remixes']}\n📥 کل دانلودها: {stats['total_downloads']}\n🔗 کانال‌های فعال: {stats['active_channels']}\n\n🏆 پربازدیدترین:\n"
        if stats['most_viewed']:
            code, title, artist, views = stats['most_viewed']
            msg += f"{code} - {title} - {artist} (👁 {views})"
        else:
            msg += "هیچ ریمیکسی موجود نیست"
        
        remixes = get_all_remixes()
        total_likes = sum(r[4] for r in remixes) if remixes else 0
        total_dislikes = sum(r[5] for r in remixes) if remixes else 0
        msg += f"\n\n📊 آمار کلی رأی‌ها:\n👍 کل لایک‌ها: {total_likes}\n👎 کل دیسلایک‌ها: {total_dislikes}\n\n📈 نرخ محبوبیت: "
        if total_likes + total_dislikes > 0:
            rate = (total_likes / (total_likes + total_dislikes)) * 100
            msg += f"{rate:.1f}% لایک"
        else:
            msg += "هنوز رأیی ثبت نشده"
        
        await update.message.reply_text(msg)
        return

    if text == "بکاپ دیتابیس 💾":
        clear_user_state(context)
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy(DATABASE_NAME, backup_name)

        await update.message.reply_text(f"بکاپ دیتابیس 💾\n\n✅ فایل بکاپ با موفقیت ایجاد شد\n📁 نام فایل: {backup_name}\n📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n⚠️ لطفاً فایل را در جای امن ذخیره کنید")

        try:
            with open(backup_name, 'rb') as f:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=f,
                    caption=f"💾 بکاپ دیتابیس - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            os.remove(backup_name)
        except Exception as e:
            logger.error(f"Error sending backup: {e}")
        return

    # ===== پردازش فایل‌ها =====
    action = context.user_data.get('admin_action')
    user_action = context.user_data.get('user_action')

    # ===== اولویت ۱: افزودن ریمیکس (پنل ادمین) =====
    if action == 'add_remix_audio':
        if update.message.audio:
            audio_file = await update.message.audio.get_file()
            code = context.user_data['new_remix_code']
            mp3_path = f"remixes/remix_{code}.mp3"
            os.makedirs("remixes", exist_ok=True)
            await audio_file.download_to_drive(mp3_path)

            title = context.user_data['new_remix_title']
            artist = context.user_data['new_remix_artist']
            cover_path = context.user_data['new_remix_cover']

            success = add_metadata_to_mp3(mp3_path, cover_path, title, artist, code)

            if success:
                add_remix(code, mp3_path, title, artist, cover_path)
                await update.message.reply_text(
                    f"ریمیکس با موفقیت ذخیره شد ✅\n\n🎵 {title} - {artist}\n🎚 کد: {code}\n🖼 عکس کاور به متادیتا اضافه شد\n\n🔗 {create_remix_link(code)}"
                )
            else:
                await update.message.reply_text("فایل ذخیره شد اما متادیتا اضافه نشد ⚠️")

            clear_user_state(context)
        else:
            await update.message.reply_text("لطفاً یک فایل MP3 معتبر ارسال کنید ❌")
        return

    # ===== اولویت ۲: دریافت ریمیکس با کد =====
    if user_action == 'get_remix_by_code':
        try:
            code = int(text.strip())
            remix = get_remix(code)
            
            if not remix:
                await update.message.reply_text(f"ریمیکس با کد {code} یافت نشد ❌")
                context.user_data.pop('user_action', None)
                return
            
            deactivate_expired_channels()
            has_reward = has_referral_reward(user_id)
            channels = get_active_channels()
            
            if not has_reward:
                is_member, failed_channel = check_all_memberships(user_id, channels, context.bot)
                if not is_member:
                    context.user_data['pending_remix'] = code
                    keyboard = create_membership_keyboard(channels)
                    text_msg = f"دریافت ریمیکس 🎵\n\nکاربر {update.effective_user.first_name or 'کاربر'} عزیز ❤️\n\nبرای دریافت نسخه کامل ریمیکس، ابتدا در کانال‌های زیر عضو شوید و سپس روی گزینه «عضو شدم ✅» ضربه بزنید\n\nپس از تأیید عضویت، فایل به صورت خودکار ارسال خواهد شد 🎧🔥"
                    await update.message.reply_text(text_msg, reply_markup=keyboard)
                    context.user_data.pop('user_action', None)
                    return
            
            code, file_path, title, artist, cover_path, views, likes, dislikes, created_at = remix
            
            increment_views(code, user_id)
            add_user_remix(user_id, code)
            
            vote_keyboard = create_vote_keyboard(code, user_id)
            caption = f"🎵 {title}\n🎤 خواننده: {artist}\n🎚 کد: {code}\n📅 تاریخ انتشار: {created_at[:10] if created_at else 'نامشخص'}\n\nاز شنیدن این ریمیکس لذت بردید؟ نظرتون رو با کلیک روی دکمه‌های زیر ثبت کنید 👇"
            
            try:
                with open(file_path, 'rb') as audio_file:
                    await update.message.reply_audio(
                        audio=audio_file,
                        title=title,
                        performer=artist,
                        caption=caption,
                        reply_markup=vote_keyboard
                    )
                context.user_data.pop('user_action', None)
            except Exception as e:
                logger.error(f"Error sending remix: {e}")
                await update.message.reply_text("خطا در ارسال فایل ❌ لطفاً بعداً تلاش کنید")
                
        except ValueError:
            await update.message.reply_text("کد معتبر نیست ❌ لطفاً یک عدد ارسال کنید")
            context.user_data.pop('user_action', None)
        except Exception as e:
            await update.message.reply_text(f"خطا ❌ {e}")
            context.user_data.pop('user_action', None)
        return

    # ===== اولویت ۳: پیشنهاد آهنگ برای ادیت =====
    if user_action == 'song_request':
        if update.message.audio:
            audio = update.message.audio
            file_id = audio.file_id
            file_name = audio.file_name or "unknown.mp3"
            
            add_song_request(user_id, file_id, file_name)
            
            user = update.effective_user
            caption = (
                f"📥 درخواست آهنگ جدید\n\n"
                f"👤 کاربر: {user.first_name}\n"
                f"🆔 آیدی: {user.id}\n"
                f"📛 یوزرنیم: @{user.username if user.username else 'ندارد'}\n"
                f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"📁 نام فایل: {file_name}"
            )
            
            try:
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
                context.user_data.pop('user_action', None)
            except Exception as e:
                logger.error(f"Error sending song request to group: {e}")
                await update.message.reply_text("خطا در ارسال درخواست ❌ لطفاً بعداً تلاش کنید")
        else:
            await update.message.reply_text("❌ لطفاً یک فایل MP3 معتبر ارسال کنید")
        return

    # ===== ادامه مدیریت سایر admin_actionها =====
    if not action:
        return

    if action == 'add_remix_code':
        try:
            code = int(text.strip())
            if get_remix(code):
                await update.message.reply_text(f"ریمیکس با کد {code} قبلاً وجود دارد ⚠️ کد دیگری وارد کنید")
                return
            context.user_data['new_remix_code'] = code
            context.user_data['admin_action'] = 'add_remix_title'
            await update.message.reply_text("عنوان آهنگ 🎵\n\nلطفاً عنوان آهنگ (Title) را وارد کنید")
        except:
            await update.message.reply_text("کد معتبر نیست ❌ یک عدد ارسال کنید")

    elif action == 'add_remix_title':
        context.user_data['new_remix_title'] = text
        context.user_data['admin_action'] = 'add_remix_artist'
        await update.message.reply_text("نام خواننده 🎤\n\nلطفاً نام خواننده (Artist) را وارد کنید")

    elif action == 'add_remix_artist':
        context.user_data['new_remix_artist'] = text
        context.user_data['admin_action'] = 'add_remix_cover'
        await update.message.reply_text("عکس کاور 🖼\n\nلطفاً عکس کاور آهنگ را ارسال کنید (حتماً با نسبت 1:1)")

    elif action == 'add_remix_cover':
        if update.message.photo:
            photo_file = await update.message.photo[-1].get_file()
            code = context.user_data['new_remix_code']
            cover_path = f"covers/code_{code}.jpg"
            os.makedirs("covers", exist_ok=True)
            await photo_file.download_to_drive(cover_path)
            context.user_data['new_remix_cover'] = cover_path
            context.user_data['admin_action'] = 'add_remix_audio'
            await update.message.reply_text("ارسال فایل MP3 🎵\n\nلطفاً فایل MP3 ریمیکس را ارسال کنید")
        else:
            await update.message.reply_text("لطفاً یک عکس ارسال کنید ❌")

    elif action == 'delete_remix':
        try:
            code = int(text.strip())
            remix = get_remix(code)
            if not remix:
                await update.message.reply_text(f"ریمیکس با کد {code} یافت نشد ❌")
                return
            
            file_path = remix[1]
            cover_path = remix[4]
            if os.path.exists(file_path):
                os.remove(file_path)
            if cover_path and os.path.exists(cover_path):
                os.remove(cover_path)
            
            delete_remix(code)
            await update.message.reply_text(f"ریمیکس با کد {code} با موفقیت حذف شد ✅")
            context.user_data.pop('admin_action', None)
        except:
            await update.message.reply_text("کد معتبر نیست ❌ یک عدد ارسال کنید")

    elif action == 'add_channel_link':
        context.user_data['new_channel_link'] = text
        context.user_data['admin_action'] = 'add_channel_name'
        await update.message.reply_text("نام نمایشی کانال 🔰\n\nلطفاً یک نام برای این کانال وارد کنید\n(مثال: کانال اصلی 🖤 یا تبلیغ 💢)")

    elif action == 'add_channel_name':
        context.user_data['new_channel_name'] = text
        context.user_data['admin_action'] = 'add_channel_days'
        await update.message.reply_text("مدت زمان اشتراک 📅\n\nلطفاً تعداد روزهای اشتراک را وارد کنید\n(مثال: 30 یا 60 یا 90)")

    elif action == 'add_channel_days':
        try:
            clean_text = text.strip().replace(" ", "").replace("روز", "").replace("روز", "")
            days = int(clean_text)
            
            if days <= 0:
                await update.message.reply_text("تعداد روز باید بیشتر از ۰ باشد ❌")
                return
                
            link = context.user_data.get('new_channel_link')
            name = context.user_data.get('new_channel_name')
            
            if not link or not name:
                await update.message.reply_text("خطا ❌ لطفاً مراحل را از اول تکرار کنید")
                return
                
            success = add_channel(link, name, days)
            if not success:
                await update.message.reply_text("این کانال قبلاً در لیست عضویت اجباری وجود دارد ⚠️")
                return
                
            await update.message.reply_text(
                f"کانال با موفقیت اضافه شد ✅\n\n🔗 {link}\n🔰 {name}\n📅 مدت: {days} روز\n📆 تاریخ انقضا: {(datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')}"
            )
            for key in ['admin_action', 'new_channel_link', 'new_channel_name']:
                context.user_data.pop(key, None)
        except ValueError:
            await update.message.reply_text("تعداد روز معتبر نیست ❌ لطفاً یک عدد (مثلاً 30) ارسال کنید")
        except Exception as e:
            await update.message.reply_text(f"خطا ❌ {e}")

    elif action == 'remove_channel':
        try:
            channel_id = int(text.strip())
            
            conn = sqlite3.connect(DATABASE_NAME)
            c = conn.cursor()
            c.execute("SELECT is_permanent FROM required_channels WHERE id = ?", (channel_id,))
            result = c.fetchone()
            conn.close()
            
            if result and result[0] == 1 and user_id != OWNER_ID:
                await update.message.reply_text("شما اجازه حذف کانال اصلی را ندارید ⛔")
                return
            
            success = remove_channel(channel_id, user_id == OWNER_ID)
            if not success:
                await update.message.reply_text("شما اجازه حذف کانال اصلی را ندارید ⛔")
                return
                
            await update.message.reply_text(f"کانال با آیدی {channel_id} با موفقیت حذف شد ✅")
            context.user_data.pop('admin_action', None)
        except:
            await update.message.reply_text("آیدی معتبر نیست ❌ یک عدد ارسال کنید")

    elif action == 'add_admin':
        try:
            admin_id = int(text.strip())
            if admin_id == OWNER_ID:
                await update.message.reply_text("مالک قبلاً ادمین است ⛔")
                return
            add_admin(admin_id, user_id)
            await update.message.reply_text(f"کاربر با آیدی {admin_id} به ادمین‌ها اضافه شد ✅")
            context.user_data.pop('admin_action', None)
        except:
            await update.message.reply_text("آیدی معتبر نیست ❌ یک عدد ارسال کنید")

    elif action == 'remove_admin':
        try:
            admin_id = int(text.strip())
            if admin_id == OWNER_ID:
                await update.message.reply_text("نمی‌توانید مالک را حذف کنید ⛔")
                return
            remove_admin(admin_id)
            await update.message.reply_text(f"ادمین با آیدی {admin_id} حذف شد ✅")
            context.user_data.pop('admin_action', None)
        except:
            await update.message.reply_text("آیدی معتبر نیست ❌ یک عدد ارسال کنید")

    elif action == 'set_price':
        try:
            price = int(text.strip())
            set_setting('ad_price_per_day', str(price))
            await update.message.reply_text(f"نرخ تبلیغات به {price} تومان در روز تغییر یافت ✅")
            context.user_data.pop('admin_action', None)
        except:
            await update.message.reply_text("مبلغ معتبر نیست ❌ یک عدد ارسال کنید")

    elif action == 'change_password':
        if len(text.strip()) >= 4:
            await update.message.reply_text(
                f"رمز پنل تغییر یافت 🔐\n\nرمز جدید: {text.strip()}\n\n⚠️ توجه: برای اعمال تغییرات، ربات را ریستارت کنید"
            )
            context.user_data.pop('admin_action', None)
        else:
            await update.message.reply_text("رمز باید حداقل ۴ کاراکتر باشد ❌")

    elif text and (text.startswith("https://t.me/") or text.startswith("t.me/")):
        if CHANNEL_USERNAME.replace("@", "") in text:
            context.user_data['pending_button_link'] = text
            context.user_data['admin_action'] = 'add_button_code'
            await update.message.reply_text("افزودن دکمه به پست 🔗\n\nلطفاً کد ریمیکس مربوط به این پست را وارد کنید")
        else:
            await update.message.reply_text("لینک باید مربوط به کانال اصلی باشد ℹ️")

    elif action == 'add_button_code':
        try:
            code = int(text.strip())
            link = context.user_data.get('pending_button_link')
            if not link:
                await update.message.reply_text("خطا ❌ لطفاً مجدداً لینک را ارسال کنید")
                return

            match = re.search(r'/(\d+)$', link)
            if not match:
                await update.message.reply_text("لینک معتبر نیست ❌ فرمت صحیح: https://t.me/EDIT_41/123")
                return

            message_id = int(match.group(1))
            chat_id = f"@{CHANNEL_USERNAME.replace('@', '')}"

            button_text = "دریافت ریمیکس کامل 🎵"
            button_url = create_remix_link(code)

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
                await update.message.reply_text(f"خطا در افزودن دکمه ❌ {e}\n\nمطمئن شوید ربات در کانال ادمین است و دسترسی ویرایش پیام دارد")

            context.user_data.pop('pending_button_link', None)
            context.user_data.pop('admin_action', None)

        except:
            await update.message.reply_text("کد معتبر نیست ❌ یک عدد ارسال کنید")


# ============================================================
# تابع مدیریت پیام‌های گروه خصوصی
# ============================================================
async def handle_group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logger.info(f"📩 پیام جدید در گروه از {user_id}")
    
    if user_id != OWNER_ID:
        logger.warning(f"⛔ کاربر {user_id} تلاش کرد در گروه پاسخ دهد")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("ℹ️ لطفاً روی پیام درخواست آهنگ ریپلای کنید و سپس ✅ یا ❌ را ارسال کنید.")
        logger.info("ℹ️ پیام ریپلای نبود")
        return
    
    reply_to = update.message.reply_to_message
    text = update.message.text.strip()
    logger.info(f"📝 ریپلای به پیام: {text}")
    
    if not reply_to.audio:
        await update.message.reply_text("ℹ️ این پیام یک درخواست آهنگ نیست (فایل صوتی ندارد).")
        logger.warning("ℹ️ پیام ریپلای شده فایل صوتی ندارد")
        return
    
    caption = reply_to.caption or ""
    logger.info(f"📄 کپشن پیام: {caption[:100]}...")
    
    if "درخواست آهنگ جدید" not in caption:
        await update.message.reply_text("ℹ️ این پیام یک درخواست آهنگ نیست (کپشن نامناسب).")
        logger.warning("ℹ️ کپشن شامل 'درخواست آهنگ جدید' نیست")
        return
    
    import re
    match = re.search(r'🆔 آیدی:\s*(\d+)', caption)
    if not match:
        await update.message.reply_text("❌ آیدی کاربر در پیام پیدا نشد.")
        logger.error("❌ آیدی کاربر در کپشن پیدا نشد")
        return
    
    target_user_id = int(match.group(1))
    file_name = reply_to.audio.file_name or "آهنگ"
    logger.info(f"🎯 کاربر هدف: {target_user_id}, فایل: {file_name}")
    
    if text == "✅":
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"✅ درخواست آهنگ شما تأیید شد!\n\nآهنگ **{file_name}** برای ادیت انتخاب شد.\nبه زودی ویدیو ادیت شده در کانال منتشر می‌شود 🎬🔥\n\n🔗 {CHANNEL_USERNAME}"
            )
            await update.message.reply_text(f"✅ پیام تأیید به کاربر ارسال شد.")
            logger.info(f"✅ پیام تأیید به {target_user_id} ارسال شد")
        except Exception as e:
            logger.error(f"❌ خطا در ارسال پیام تأیید: {e}")
            await update.message.reply_text(f"❌ خطا در ارسال پیام: {e}")
        
    elif text == "❌":
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"❌ درخواست آهنگ شما متأسفانه تأیید نشد.\n\nآهنگ **{file_name}** برای ادیت مناسب نبود.\nمی‌توانید {REQUEST_COOLDOWN_DAYS} روز دیگر آهنگ دیگری پیشنهاد دهید.\n\n🔗 {CHANNEL_USERNAME}"
            )
            await update.message.reply_text(f"❌ پیام رد به کاربر ارسال شد.")
            logger.info(f"❌ پیام رد به {target_user_id} ارسال شد")
        except Exception as e:
            logger.error(f"❌ خطا در ارسال پیام رد: {e}")
            await update.message.reply_text(f"❌ خطا در ارسال پیام: {e}")
    
    else:
        await update.message.reply_text("ℹ️ فقط با ✅ یا ❌ می‌توانید پاسخ دهید.")
        logger.info(f"ℹ️ متن نامعتبر: {text}")


# ============================================================
# تابع دستور /admin
# ============================================================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == OWNER_ID or is_admin(user_id):
        clear_user_state(context)
        keyboard = create_admin_main_keyboard()
        await update.message.reply_text(
            "پنل مدیریت 🔧\n\nلطفاً یکی از بخش‌های زیر را انتخاب کنید",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text("شما دسترسی به پنل ادمین ندارید ⛔")


# ============================================================
# تابع دستور /addbutton
# ============================================================
async def add_button_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not (user_id == OWNER_ID or is_admin(user_id)):
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
        button_url = create_remix_link(code)
        
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
            await update.message.reply_text(f"خطا در افزودن دکمه ❌ {e}\n\nمطمئن شوید ربات در کانال ادمین است و دسترسی ویرایش پیام دارد")
            
    except ValueError:
        await update.message.reply_text("کد ریمیکس باید یک عدد باشد ❌")
    except Exception as e:
        await update.message.reply_text(f"خطا ❌ {e}")


# ============================================================
# تابع رویداد خروج از کانال
# ============================================================
async def handle_channel_leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                logger.info(f"User {user_id} left channel, notification sent.")
            except Exception as e:
                logger.error(f"Could not send leave notification to {user_id}: {e}")

        elif new_status == "member":
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"خوش برگشتی 🎉\n\n{CHANNEL_USERNAME}\n\nهمیشه منتظر ریمیکس‌های جدید باش 💪\n\n🔗 برای دریافت ریمیکس، روی لینک‌های زیر پست‌ها کلیک کنید"
                )
                logger.info(f"User {user_id} rejoined channel, welcome back sent.")
            except Exception as e:
                logger.error(f"Could not send rejoin notification to {user_id}: {e}")


# ============================================================
# تابع بکاپ خودکار
# ============================================================
async def auto_backup(context: ContextTypes.DEFAULT_TYPE):
    try:
        backup_name = f"backup_auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy(DATABASE_NAME, backup_name)

        with open(backup_name, 'rb') as f:
            await context.bot.send_document(
                chat_id=OWNER_ID,
                document=f,
                caption=f"💾 بکاپ خودکار - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        os.remove(backup_name)
        logger.info("Auto backup completed and sent to owner.")
    except Exception as e:
        logger.error(f"Auto backup failed: {e}")


# ============================================================
# تابع main
# ============================================================
def main():
    init_db()
    logger.info("✅ دیتابیس راه‌اندازی شد.")

    os.makedirs("remixes", exist_ok=True)
    os.makedirs("covers", exist_ok=True)
    logger.info("✅ پوشه‌های مورد نیاز ایجاد شدند.")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("addbutton", add_button_command))

    app.add_handler(CallbackQueryHandler(callback_handler))

    # ===== ترتیب هندلرها =====
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT, handle_group_messages))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(MessageHandler(filters.AUDIO, handle_message))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_channel_leave))

    job_queue = app.job_queue
    if job_queue:
        current_jobs = job_queue.jobs()
        for job in current_jobs:
            if job.name == "auto_backup":
                job.schedule_removal()
                logger.info("🔄 Job قبلی بکاپ حذف شد.")
        
        job_queue.run_repeating(
            auto_backup, 
            interval=86400,
            first=60,
            name="auto_backup"
        )
        logger.info("✅ JobQueue برای بکاپ خودکار (هر ۲۴ ساعت) راه‌اندازی شد.")
    else:
        logger.warning("⚠️ JobQueue در دسترس نیست! بکاپ خودکار غیرفعال است.")

    print(f"""
✅ ربات EDIT 41 با موفقیت روشن شد

🤖 نام ربات: {BOT_USERNAME}
👤 مالک: @JENERAL_41
🔗 کانال: {CHANNEL_USERNAME}
📊 دیتابیس: {DATABASE_NAME}

⚙️ قابلیت‌های فعال:
✅ عضویت اجباری چندگانه
✅ پنل ادمین چندلایه
✅ آپلود ریمیکس با متادیتا
✅ دکمه‌های 👍 و 👎
✅ ریمیکس‌های برتر
✅ ریمیکس تصادفی
✅ دریافت ریمیکس با کد
✅ پیشنهاد آهنگ برای ادیت
✅ سیستم دعوت دوستان
✅ پنل آمار کامل
✅ بکاپ خودکار (هر ۲۴ ساعت)
✅ پیام اخطار خروج از کانال
✅ افزودن خودکار دکمه با لینک
✅ تشخیص خودکار مالک
""")

    app.run_polling()


if __name__ == "__main__":
    main()