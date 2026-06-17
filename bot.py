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

admin_session = {}
user_first_start = {}

# ============================================================
# تابع کمکی
# ============================================================
def clear_user_state(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('admin_action', None)
    context.user_data.pop('user_action', None)
    context.user_data.pop('new_remix_code', None)
    context.user_data.pop('new_remix_title', None)
    context.user_data.pop('new_remix_artist', None)
    context.user_data.pop('new_remix_cover', None)
    context.user_data.pop('new_channel_link', None)
    context.user_data.pop('new_channel_name', None)
    context.user_data.pop('pending_button_link', None)
    context.user_data.pop('feature_action', None)
    context.user_data.pop('new_remix_path', None)

def is_owner_or_admin(user_id):
    return user_id == OWNER_ID or is_admin(user_id)

# ============================================================
# تابع start
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "کاربر"
    first_name = update.effective_user.first_name or "کاربر"

    add_user(user_id, username, first_name)
    args = context.args
    
    logger.info(f"📩 Start from user {user_id}, args: {args}")

    # ===== لینک دعوت =====
    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0].split("ref_")[1])
            if referrer_id != user_id:
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
                activate_referral_reward(user_id, REQUEST_COOLDOWN_DAYS, 'referred')
                return
        except Exception as e:
            logger.error(f"❌ Error processing referral: {e}")

    # ===== لینک ریمیکس =====
    if args and args[0].startswith("code_"):
        try:
            code_str = args[0].split("code_")[1]
            remix_code = int(code_str)
            logger.info(f"✅ Code extracted: {remix_code}")
            context.user_data['pending_remix'] = remix_code
            await check_and_send_remix(update, context, remix_code)
            return
        except ValueError as e:
            logger.error(f"❌ ValueError extracting code: {e}")
            await update.message.reply_text("لینک نامعتبر است ❌\nفرمت صحیح: https://t.me/EDIT_41_BOT?start=code_1")
            return
        except Exception as e:
            logger.error(f"❌ Error extracting code: {e}")
            await update.message.reply_text("لینک نامعتبر است ❌")
            return

    # ===== مالک =====
    if user_id == OWNER_ID:
        clear_user_state(context)
        admin_session[user_id] = {'verified': True}
        keyboard = create_admin_main_keyboard()
        await update.message.reply_text(
            f"👑 خوش آمدید مالک عزیز!\n\n{CHANNEL_USERNAME}\n\n🔧 پنل مدیریت\nلطفاً یکی از بخش‌های زیر را انتخاب کنید:",
            reply_markup=keyboard
        )
        return

    # ===== کاربر عادی (اولین بار) =====
    is_new = user_id not in user_first_start
    if is_new:
        user_first_start[user_id] = True
        welcome_text = (
            f"🎵 به ربات EDIT 41 خوش آمدید!\n\n"
            f"💠 {CHANNEL_USERNAME}\n"
            f"بهترین کانال ادیت و ریمیکس‌های رپ\n\n"
            f"🔥 اینجا می‌توانید:\n"
            f"✅ ریمیکس‌های جدید و انحصاری را دریافت کنید\n"
            f"✅ به آهنگ‌ها امتیاز دهید و در قرعه‌کشی هفتگی شرکت کنید\n"
            f"✅ آهنگ مورد نظر خود را برای ادیت پیشنهاد دهید\n\n"
            f"📌 راهنمای سریع:\n"
            f"• برای دریافت ریمیکس، روی دکمه‌های زیر کلیک کنید\n"
            f"• با لایک 👍 به ریمیکس‌ها امتیاز دهید و شانس خود را افزایش دهید\n\n"
            f"💠 {CHANNEL_USERNAME}\n"
            f"🔗 @{BOT_USERNAME.replace('@', '')}"
        )
    else:
        welcome_text = (
            f"🎵 به ربات EDIT 41 خوش آمدید!\n\n"
            f"{CHANNEL_USERNAME}\n"
            f"بهترین کانال ادیت و ریمیکس‌های فوق‌العاده\n\n"
            f"برای دریافت ریمیکس، روی دکمه‌های زیر کلیک کنید"
        )

    keyboard = create_user_keyboard()
    await update.message.reply_text(welcome_text, reply_markup=keyboard)


# ============================================================
# تابع بررسی و ارسال ریمیکس (اصلاح شده)
# ============================================================
async def check_and_send_remix(update: Update, context: ContextTypes.DEFAULT_TYPE, remix_code):
    user_id = update.effective_user.id
    username = update.effective_user.first_name or "کاربر"

    logger.info(f"🔍 check_and_send_remix: user {user_id}, code {remix_code}")

    deactivate_expired_channels()
    has_reward = has_referral_reward(user_id)
    
    channels = get_active_channels()
    
    # حذف کانال‌های تکراری بر اساس channel_link
    seen = set()
    unique_channels = []
    for ch in channels:
        if ch[1] not in seen:
            seen.add(ch[1])
            unique_channels.append(ch)
    channels = unique_channels
    logger.info(f"🔍 Active channels (unique): {channels}")

    if not has_reward:
        is_member, failed_channel = check_all_memberships(user_id, channels, context.bot)
        logger.info(f"🔍 Membership check: is_member={is_member}")
        
        if not is_member:
            context.user_data['pending_remix'] = remix_code
            keyboard = create_membership_keyboard(channels)
            text = f"🎵 دریافت ریمیکس\n\nکاربر {username} عزیز ❤️\n\nبرای دریافت نسخه کامل ريمیکس، ابتدا در کانال‌های زیر عضو شوید و سپس روی گزینه «عضو شدم ✅» ضربه بزنید\n\nپس از تأیید عضویت، فایل به صورت خودکار ارسال خواهد شد 🎧🔥"
            await update.message.reply_text(text, reply_markup=keyboard)
            return

    remix = get_remix(remix_code)
    if not remix:
        logger.error(f"❌ Remix {remix_code} not found")
        await update.message.reply_text("ریمیکس مورد نظر یافت نشد ❌")
        return

    code, file_path, title, artist, cover_path, views, likes, dislikes, created_at = remix
    
    increment_views(code, user_id)
    add_user_remix(user_id, code)
    
    if not has_user_received_remix(user_id, code):
        add_points(user_id, 1, "download")

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
        logger.info(f"✅ Remix {code} sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending remix: {e}")
        await update.message.reply_text("خطا در ارسال فایل ❌ لطفاً بعداً تلاش کنید")


# ============================================================
# تابع Callback Handler (اصلاح شده)
# ============================================================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    logger.info(f"📩 Callback: {data} from {user_id}")

    if data == "check_membership":
        logger.info(f"✅ check_membership called for user {user_id}")
        
        remix_code = context.user_data.get('pending_remix')
        if not remix_code:
            await query.edit_message_text("خطا ❌ لطفاً دوباره از لینک وارد شوید")
            return

        deactivate_expired_channels()
        channels = get_active_channels()
        
        seen = set()
        unique_channels = []
        for ch in channels:
            if ch[1] not in seen:
                seen.add(ch[1])
                unique_channels.append(ch)
        channels = unique_channels
        
        has_reward = has_referral_reward(user_id)

        is_member = True
        if not has_reward:
            for channel_id, channel_link, display_name in channels:
                if not check_user_in_channel(user_id, channel_link, context.bot):
                    is_member = False
                    logger.info(f"❌ User not in channel: {channel_link}")
                    break

        if not is_member:
            await query.answer("❌ در همه کانال‌ها عضو نشده‌اید!", show_alert=True)
            keyboard = create_membership_keyboard(channels)
            await query.edit_message_reply_markup(reply_markup=keyboard)
            return

        await query.edit_message_text("✅ عضویت شما تأیید شد! در حال ارسال فایل...")

        remix = get_remix(remix_code)
        if remix:
            code, file_path, title, artist, cover_path, views, likes, dislikes, created_at = remix
            increment_views(code, user_id)
            add_user_remix(user_id, code)
            
            if not has_user_received_remix(user_id, code):
                add_points(user_id, 1, "download")

            vote_keyboard = create_vote_keyboard(code, user_id)
            caption = f"🎵 {title}\n🎤 خواننده: {artist}\n🎚 کد: {code}\n📅 تاریخ انتشار: {created_at[:10] if created_at else 'نامشخص'}\n\n🎧 از شنیدن این ریمیکس لذت بردید؟ نظرتون رو با کلیک روی دکمه‌های زیر ثبت کنید 👇"
            
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
                logger.info(f"✅ Remix {code} sent via callback to {user_id}")
            except Exception as e:
                logger.error(f"Error sending remix via callback: {e}")
                await context.bot.send_message(user_id, "خطا در ارسال فایل ❌")
        else:
            await context.bot.send_message(user_id, "ریمیکس یافت نشد ❌")

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

    if update.message.audio or update.message.photo:
        await handle_file_upload(update, context)
        return

    # ===== تشخیص دکمه‌های کاربران عادی =====
    if not (user_id == OWNER_ID or is_admin(user_id)):
        if text == "ریمیکس تصادفی 🎲":
            if not is_feature_enabled('feature_random_remix'):
                await update.message.reply_text("این قابلیت توسط مدیریت غیرفعال شده است ⛔")
                return
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
            if not is_feature_enabled('feature_top_remixes'):
                await update.message.reply_text("این قابلیت توسط مدیریت غیرفعال شده است ⛔")
                return
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

        if text == "دریافت ریمیکس با کد 📥":
            if not is_feature_enabled('feature_get_by_code'):
                await update.message.reply_text("این قابلیت توسط مدیریت غیرفعال شده است ⛔")
                return
            clear_user_state(context)
            context.user_data['user_action'] = 'get_remix_by_code'
            await update.message.reply_text(
                "دریافت ریمیکس با کد 📥\n\n"
                "لطفاً کد عددی ریمیکس مورد نظر را وارد کنید:\n"
                "(مثال: 15)"
            )
            return

        if text == "پیشنهاد آهنگ برای ادیت 📤":
            if not is_feature_enabled('feature_song_request'):
                await update.message.reply_text("این قابلیت توسط مدیریت غیرفعال شده است ⛔")
                return
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

        if text == "دعوت دوستان 🎁":
            ref_link = create_referral_link(user_id)
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
            return

        if text == "راهنما ℹ️":
            if not is_feature_enabled('feature_help'):
                await update.message.reply_text("این قابلیت توسط مدیریت غیرفعال شده است ⛔")
                return
            msg = f"راهنما ℹ️\n\n🎵 دریافت ریمیکس:\nروی لینک زیر هر پست در کانال کلیک کنید\n\n🎲 ریمیکس تصادفی:\nاز منوی اصلی گزینه مربوطه را انتخاب کنید\n\n🏆 ریمیکس‌های برتر:\nمشاهده پربازدیدترین و محبوب‌ترین ریمیکس‌ها\n\n📊 آمار ربات:\nمشاهده آمار کلی ربات\n\n🔗 کانال اصلی:\n{CHANNEL_USERNAME}"
            await update.message.reply_text(msg)
            return

        return

    # ===== مالک یا ادمین: پنل مدیریت =====
    action = context.user_data.get('admin_action')
    feature_action = context.user_data.get('feature_action')

    if text == "پنل ریمیکس 🎵":
        clear_user_state(context)
        keyboard = create_remix_panel_keyboard()
        await update.message.reply_text("پنل ریمیکس 🎵\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید", reply_markup=keyboard)
        return

    if text == "پنل عضویت اجباری 🔗":
        clear_user_state(context)
        keyboard = create_channel_panel_keyboard()
        await update.message.reply_text("پنل عضویت اجباری 🔗\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید", reply_markup=keyboard)
        return

    if text == "پنل ادمین 👥":
        clear_user_state(context)
        keyboard = create_admin_management_keyboard()
        await update.message.reply_text("پنل ادمین 👥\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید", reply_markup=keyboard)
        return

    if text == "پنل تنظیمات ⚙️":
        clear_user_state(context)
        keyboard = create_settings_panel_keyboard()
        await update.message.reply_text("پنل تنظیمات ⚙️\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید", reply_markup=keyboard)
        return

    if text == "بستن پنل ❌":
        clear_user_state(context)
        keyboard = create_user_keyboard()
        await update.message.reply_text("پنل مدیریت بسته شد ✅", reply_markup=keyboard)
        return

    if text == "بازگشت ↩️":
        clear_user_state(context)
        keyboard = create_admin_main_keyboard()
        await update.message.reply_text("بازگشت به منوی اصلی ↩️", reply_markup=keyboard)
        return

    # ===== پنل ریمیکس =====
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

    if text == "آمار ریمیکس 💎":
        clear_user_state(context)
        remixes = get_all_remixes()
        total_remixes = len(remixes)
        
        total_downloads = get_total_remix_downloads()
        total_views = sum(r[3] for r in remixes) if remixes else 0
        
        top_views = get_top_remixes_by_views(1)
        top_likes = get_top_remixes_by_likes(1)
        
        total_likes = sum(r[4] for r in remixes) if remixes else 0
        total_dislikes = sum(r[5] for r in remixes) if remixes else 0
        
        msg = f"آمار ریمیکس 💎\n\n🎵 کل ریمیکس‌ها: {total_remixes}\n📥 کل دانلودها: {total_downloads}\n👁 کل بازدیدها: {total_views}\n\n🏆 پربازدیدترین:\n"
        if top_views:
            code, title, artist, views, likes, dislikes, created_at = top_views[0]
            msg += f"`{code}` - {title} - {artist} (👁 {views})"
        else:
            msg += "هیچ ریمیکسی موجود نیست"
        
        msg += f"\n\n❤️ پرطرفدارترین:\n"
        if top_likes:
            code, title, artist, views, likes, dislikes, created_at, score = top_likes[0]
            msg += f"`{code}` - {title} - {artist} (⭐ {score})"
        else:
            msg += "هیچ ریمیکسی موجود نیست"
        
        msg += f"\n\n📊 آمار کلی رأی‌ها:\n👍 کل لایک‌ها: {total_likes}\n👎 کل دیسلایک‌ها: {total_dislikes}\n\n📈 نرخ محبوبیت: "
        if total_likes + total_dislikes > 0:
            rate = (total_likes / (total_likes + total_dislikes)) * 100
            msg += f"{rate:.1f}% لایک"
        else:
            msg += "هنوز رأیی ثبت نشده"
        
        await update.message.reply_text(msg)
        return

    if text == "جستجوی ریمیکس با کد 🔍":
        clear_user_state(context)
        context.user_data['admin_action'] = 'search_remix'
        await update.message.reply_text("جستجوی ریمیکس 🔍\n\nلطفاً کد ریمیکس مورد نظر را وارد کنید")
        return

    # ===== پنل عضویت =====
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

    # ===== پنل ادمین =====
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

    # ===== پنل تنظیمات =====
    if text == "وضعیت قابلیت‌ها ⚙️":
        clear_user_state(context)
        features = get_all_features()
        
        msg = "وضعیت قابلیت‌ها ⚙️\n\n"
        for key, data in features.items():
            status_emoji = "✅" if data['status'] == 'on' else "❌"
            msg += f"{data['name']} {status_emoji}\n"
        
        keyboard = create_feature_status_keyboard()
        await update.message.reply_text(msg, reply_markup=keyboard)
        return

    if text == "خاموش کردن قابلیت 🛑":
        features = get_all_features()
        on_features = [k for k, v in features.items() if v['status'] == 'on']
        if not on_features:
            await update.message.reply_text("همه قابلیت‌ها در حال حاضر خاموش هستند ❌")
            return
        
        msg = "خاموش کردن قابلیت 🛑\n\nلطفاً شماره قابلیت مورد نظر را وارد کنید:\n\n"
        for i, key in enumerate(on_features, 1):
            msg += f"{i}. {features[key]['name']}\n"
        
        context.user_data['feature_action'] = 'turn_off'
        context.user_data['feature_list'] = on_features
        await update.message.reply_text(msg)
        return

    if text == "روشن کردن قابلیت ✅":
        features = get_all_features()
        off_features = [k for k, v in features.items() if v['status'] == 'off']
        if not off_features:
            await update.message.reply_text("همه قابلیت‌ها در حال حاضر روشن هستند ✅")
            return
        
        msg = "روشن کردن قابلیت ✅\n\nلطفاً شماره قابلیت مورد نظر را وارد کنید:\n\n"
        for i, key in enumerate(off_features, 1):
            msg += f"{i}. {features[key]['name']}\n"
        
        context.user_data['feature_action'] = 'turn_on'
        context.user_data['feature_list'] = off_features
        await update.message.reply_text(msg)
        return

    if text == "آمار کاربران 👥":
        clear_user_state(context)
        top_users = get_top_users(5)
        winners = get_weekly_winners()
        
        msg = "آمار کاربران 👥\n\n🏆 برترین‌های این هفته:\n\n"
        
        if top_users:
            for i, (user_id, points) in enumerate(top_users, 1):
                user = get_user(user_id)
                name = user[2] if user else "کاربر ناشناس"
                username = user[1] if user else "ندارد"
                emoji = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1] if i <= 5 else "•"
                msg += f"{emoji} {name} — {points} امتیاز\n🆔 {user_id}\n📛 @{username}\n\n"
        else:
            msg += "هیچ کاربری امتیازی کسب نکرده است\n"
        
        msg += f"📅 این آمار هر هفته یکشنبه ساعت ۰۰:۰۰ ریست می‌شود\n"
        msg += f"🏆 ۳ نفر اول هر هفته، ۳ روز عضویت رایگان دریافت می‌کنند\n\n"
        
        if winners:
            msg += "🏆 برترین‌های هفته گذشته:\n"
            for user_id, points, week_start in winners[:3]:
                user = get_user(user_id)
                name = user[2] if user else "کاربر ناشناس"
                msg += f"• {name} — {points} امتیاز\n"
        
        await update.message.reply_text(msg)
        return

    if text == "آمار کامل 📊":
        clear_user_state(context)
        stats = get_stats()
        msg = (
            f"آمار کامل 📊\n\n"
            f"👥 کل کاربران: {stats['total_users']}\n"
            f"📈 کاربران امروز: {stats['today_users']}\n"
            f"🎵 کل ریمیکس‌ها: {stats['total_remixes']}\n"
            f"📥 کل دانلودها: {stats['total_downloads']}\n"
            f"📥 دانلودهای امروز: {stats['today_downloads']}\n"
            f"👁 کل بازدیدها: {stats['total_views']}\n"
            f"🔗 کانال‌های فعال: {stats['active_channels']}\n"
            f"📝 کل درخواست‌ها: {stats['total_requests']}\n"
            f"📝 درخواست‌های امروز: {stats['today_requests']}\n\n"
            f"🏆 پربازدیدترین:\n"
        )
        if stats['most_viewed']:
            code, title, artist, views = stats['most_viewed']
            msg += f"`{code}` - {title} - {artist} (👁 {views})"
        else:
            msg += "هیچ ریمیکسی موجود نیست"
        
        msg += f"\n\n❤️ پرطرفدارترین:\n"
        if stats['most_liked']:
            code, title, artist, likes = stats['most_liked']
            msg += f"`{code}` - {title} - {artist} (👍 {likes})"
        else:
            msg += "هیچ ریمیکسی موجود نیست"
        
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

    # ===== پردازش ورودی‌های عددی برای ویژگی‌ها =====
    if feature_action in ['turn_off', 'turn_on']:
        try:
            index = int(text.strip()) - 1
            feature_list = context.user_data.get('feature_list', [])
            if 0 <= index < len(feature_list):
                feature_key = feature_list[index]
                new_status = 'off' if feature_action == 'turn_off' else 'on'
                set_feature_status(feature_key, new_status)
                status_text = "خاموش" if new_status == 'off' else "روشن"
                await update.message.reply_text(f"✅ قابلیت با موفقیت {status_text} شد")
            else:
                await update.message.reply_text("❌ شماره نامعتبر است")
        except:
            await update.message.reply_text("❌ لطفاً یک شماره معتبر ارسال کنید")
        
        context.user_data.pop('feature_action', None)
        context.user_data.pop('feature_list', None)
        return

    # ===== پردازش سایر admin_actionها =====
    if action == 'add_remix_code':
        try:
            code = int(text.strip())
            if get_remix(code):
                await update.message.reply_text(f"ریمیکس با کد {code} قبلاً وجود دارد ⚠️")
                return
            context.user_data['new_remix_code'] = code
            context.user_data['admin_action'] = 'add_remix_audio'
            await update.message.reply_text("ارسال فایل MP3 🎵\n\nلطفاً فایل MP3 ریمیکس را ارسال کنید")
        except:
            await update.message.reply_text("کد معتبر نیست ❌ یک عدد ارسال کنید")
        return

    if action == 'search_remix':
        try:
            code = int(text.strip())
            remix = get_remix(code)
            if not remix:
                await update.message.reply_text(f"ریمیکس با کد {code} یافت نشد ❌")
                context.user_data.pop('admin_action', None)
                return
            
            code, file_path, title, artist, cover_path, views, likes, dislikes, created_at = remix
            msg = (
                f"🔍 نتیجه جستجو\n\n"
                f"🎵 {title}\n"
                f"🎤 خواننده: {artist}\n"
                f"🎚 کد: {code}\n"
                f"📅 تاریخ انتشار: {created_at[:10] if created_at else 'نامشخص'}\n"
                f"👁 بازدید: {views}\n"
                f"👍 لایک: {likes}\n"
                f"👎 دیسلایک: {dislikes}\n"
                f"📥 دانلودها: {get_total_remix_downloads()}\n\n"
                f"🔗 لینک دریافت:\n{create_remix_link(code)}"
            )
            await update.message.reply_text(msg)
            context.user_data.pop('admin_action', None)
        except:
            await update.message.reply_text("کد معتبر نیست ❌ یک عدد ارسال کنید")
        return

    if action == 'delete_remix':
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
        return

    # ===== افزودن لینک پست بعد از ذخیره ریمیکس =====
    if action == 'add_remix_link':
        link = text.strip()
        code = context.user_data.get('new_remix_code')
        
        if not code:
            await update.message.reply_text("خطا ❌ کد ریمیکس پیدا نشد")
            context.user_data.pop('admin_action', None)
            return
        
        if not (link.startswith("https://t.me/") or link.startswith("t.me/")):
            await update.message.reply_text("لینک معتبر نیست ❌\nلطفاً لینک پست کانال را ارسال کنید")
            return
        
        if CHANNEL_USERNAME.replace("@", "") not in link:
            await update.message.reply_text(f"لینک باید مربوط به کانال {CHANNEL_USERNAME} باشد ❌")
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
                f"✅ ریمیکس با موفقیت ذخیره شد و دکمه زیر پست اضافه شد!\n\n"
                f"🎚 کد: {code}\n"
                f"🔗 پست: {link}\n"
                f"🔗 لینک دکمه: {button_url}"
            )
            logger.info(f"✅ Remix {code} saved and button added to post {message_id}")
        except Exception as e:
            await update.message.reply_text(f"❌ ریمیکس ذخیره شد اما خطا در افزودن دکمه:\n{e}\n\nمطمئن شوید ربات در کانال ادمین است و دسترسی ویرایش پیام دارد")
        
        context.user_data.pop('admin_action', None)
        context.user_data.pop('new_remix_code', None)
        context.user_data.pop('new_remix_path', None)
        return

    # ===== افزودن کانال =====
    if action == 'add_channel_link':
        context.user_data['new_channel_link'] = text
        context.user_data['admin_action'] = 'add_channel_name'
        await update.message.reply_text("نام نمایشی کانال 🔰\n\nلطفاً یک نام برای این کانال وارد کنید\n(مثال: کانال اصلی 🖤)")
        return

    if action == 'add_channel_name':
        context.user_data['new_channel_name'] = text
        context.user_data['admin_action'] = 'add_channel_days'
        await update.message.reply_text("مدت زمان اشتراک 📅\n\nلطفاً تعداد روزهای اشتراک را وارد کنید\n(مثال: 30)")
        return

    if action == 'add_channel_days':
        try:
            clean_text = text.strip().replace(" ", "").replace("روز", "")
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
        return

    if action == 'remove_channel':
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
        return

    if action == 'add_admin':
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
        return

    if action == 'remove_admin':
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
        return

    # ===== افزودن دکمه با لینک (دستی) =====
    if text and (text.startswith("https://t.me/") or text.startswith("t.me/")):
        if CHANNEL_USERNAME.replace("@", "") in text:
            context.user_data['pending_button_link'] = text
            context.user_data['admin_action'] = 'add_button_code'
            await update.message.reply_text("افزودن دکمه به پست 🔗\n\nلطفاً کد ریمیکس مربوط به این پست را وارد کنید")
        else:
            await update.message.reply_text("لینک باید مربوط به کانال اصلی باشد ℹ️")
        return

    if action == 'add_button_code':
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
        return


# ============================================================
# تابع پردازش فایل‌ها
# ============================================================
async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    action = context.user_data.get('admin_action')
    user_action = context.user_data.get('user_action')

    if update.message.audio:
        logger.info(f"🎵 Audio from {user_id}, action: {action}, user_action: {user_action}")
        
        if action == 'add_remix_audio':
            try:
                audio_file = await update.message.audio.get_file()
                code = context.user_data.get('new_remix_code')
                
                if not code:
                    await update.message.reply_text("خطا ❌ کد ریمیکس پیدا نشد. لطفاً مراحل را از اول تکرار کنید.")
                    return
                    
                mp3_path = f"remixes/remix_{code}.mp3"
                os.makedirs("remixes", exist_ok=True)
                await audio_file.download_to_drive(mp3_path)
                
                context.user_data['new_remix_path'] = mp3_path
                context.user_data['admin_action'] = 'add_remix_link'
                await update.message.reply_text(
                    f"✅ فایل MP3 با موفقیت دریافت شد!\n\n"
                    f"🎚 کد: {code}\n\n"
                    f"🔗 لطفاً لینک پست کانال را ارسال کنید:\n"
                    f"(مثال: https://t.me/EDIT_41/123)"
                )
                logger.info(f"✅ MP3 received for remix {code}, waiting for post link")
                return
            except Exception as e:
                logger.error(f"❌ Error receiving audio: {e}")
                await update.message.reply_text(f"خطا در دریافت فایل ❌: {e}")
                return

        elif user_action == 'song_request':
            try:
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
                logger.info(f"✅ Song request sent to group from {user_id}")
                return
            except Exception as e:
                logger.error(f"❌ Error sending song request: {e}")
                await update.message.reply_text("خطا در ارسال درخواست ❌ لطفاً بعداً تلاش کنید")
                return

        else:
            await update.message.reply_text("❌ لطفاً ابتدا از منوی اصلی گزینه مورد نظر را انتخاب کنید.")
            return

    if update.message.photo:
        await update.message.reply_text("❌ لطفاً فقط فایل MP3 ارسال کنید. (مرحله عکس کاور حذف شده است)")
        return


# ============================================================
# تابع مدیریت گروه خصوصی
# ============================================================
async def handle_group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID:
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("ℹ️ لطفاً روی پیام درخواست آهنگ ریپلای کنید و سپس ✅ یا ❌ را ارسال کنید.")
        return
    
    reply_to = update.message.reply_to_message
    text = update.message.text.strip()
    
    if not reply_to.audio:
        await update.message.reply_text("ℹ️ این پیام یک درخواست آهنگ نیست.")
        return
    
    caption = reply_to.caption or ""
    if "درخواست آهنگ جدید" not in caption:
        await update.message.reply_text("ℹ️ این پیام یک درخواست آهنگ نیست.")
        return
    
    import re
    match = re.search(r'🆔 آیدی:\s*(\d+)', caption)
    if not match:
        await update.message.reply_text("❌ آیدی کاربر در پیام پیدا نشد.")
        return
    
    target_user_id = int(match.group(1))
    file_name = reply_to.audio.file_name or "آهنگ"
    
    if text == "✅":
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"✅ درخواست آهنگ شما تأیید شد!\n\nآهنگ **{file_name}** برای ادیت انتخاب شد.\nبه زودی ویدیو ادیت شده در کانال منتشر می‌شود 🎬🔥\n\n🔗 {CHANNEL_USERNAME}"
            )
            await update.message.reply_text(f"✅ پیام تأیید به کاربر ارسال شد.")
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در ارسال پیام: {e}")
        
    elif text == "❌":
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"❌ درخواست آهنگ شما متأسفانه تأیید نشد.\n\nآهنگ **{file_name}** برای ادیت مناسب نبود.\nمی‌توانید {REQUEST_COOLDOWN_DAYS} روز دیگر آهنگ دیگری پیشنهاد دهید.\n\n🔗 {CHANNEL_USERNAME}"
            )
            await update.message.reply_text(f"❌ پیام رد به کاربر ارسال شد.")
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در ارسال پیام: {e}")
    
    else:
        await update.message.reply_text("ℹ️ فقط با ✅ یا ❌ می‌توانید پاسخ دهید.")


# ============================================================
# تابع دستورات
# ============================================================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_owner_or_admin(user_id):
        clear_user_state(context)
        keyboard = create_admin_main_keyboard()
        await update.message.reply_text(
            "پنل مدیریت 🔧\n\nلطفاً یکی از بخش‌های زیر را انتخاب کنید",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text("شما دسترسی به پنل ادمین ندارید ⛔")

async def add_button_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_owner_or_admin(user_id):
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
            except Exception as e:
                logger.error(f"Could not send leave notification: {e}")

        elif new_status == "member":
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"خوش برگشتی 🎉\n\n{CHANNEL_USERNAME}\n\nهمیشه منتظر ریمیکس‌های جدید باش 💪\n\n🔗 برای دریافت ریمیکس، روی لینک‌های زیر پست‌ها کلیک کنید"
                )
            except Exception as e:
                logger.error(f"Could not send rejoin notification: {e}")


# ============================================================
# تابع گزارش هفتگی
# ============================================================
async def weekly_report(context: ContextTypes.DEFAULT_TYPE):
    try:
        report = get_weekly_report()
        top_users = get_top_users(3)
        
        msg = (
            f"📊 گزارش هفتگی ربات\n\n"
            f"👥 کاربران جدید: {report['new_users']}\n"
            f"📥 دانلودهای جدید: {report['new_downloads']}\n"
            f"📝 درخواست‌های جدید: {report['new_requests']}\n\n"
            f"🏆 پربازدیدترین ریمیکس‌های هفته:\n"
        )
        
        if report['top_remixes']:
            for code, title, artist, views in report['top_remixes']:
                msg += f"• {title} - {artist} (👁 {views})\n"
        else:
            msg += "هیچ ریمیکسی موجود نیست\n"
        
        msg += f"\n🏅 برترین‌های این هفته:\n"
        if top_users:
            for i, (user_id, points) in enumerate(top_users, 1):
                user = get_user(user_id)
                name = user[2] if user else "کاربر ناشناس"
                msg += f"{i}. {name} — {points} امتیاز\n"
        else:
            msg += "هیچ کاربری امتیازی کسب نکرده است\n"
        
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=msg
        )
        logger.info("✅ Weekly report sent to owner")
    except Exception as e:
        logger.error(f"❌ Error sending weekly report: {e}")


# ============================================================
# تابع ریست هفتگی امتیازها
# ============================================================
async def reset_weekly_points_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        top_users = reset_weekly_points()
        logger.info(f"✅ Weekly points reset. Top users: {top_users}")
        
        if top_users:
            msg = "🔄 امتیازهای هفتگی ریست شد.\n\n🏆 برترین‌های این هفته:\n"
            for user_id, points in top_users[:3]:
                user = get_user(user_id)
                name = user[2] if user else "کاربر ناشناس"
                msg += f"• {name} — {points} امتیاز (۳ روز عضویت رایگان)\n"
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=msg
            )
    except Exception as e:
        logger.error(f"❌ Error resetting weekly points: {e}")


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

    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT, handle_group_messages))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.AUDIO, handle_file_upload))
    app.add_handler(MessageHandler(filters.PHOTO, handle_file_upload))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_channel_leave))

    job_queue = app.job_queue
    if job_queue:
        job_queue.run_daily(
            weekly_report,
            time=datetime.strptime("09:00", "%H:%M").time(),
            days=(6,),
            name="weekly_report"
        )
        
        job_queue.run_daily(
            reset_weekly_points_job,
            time=datetime.strptime("00:00", "%H:%M").time(),
            days=(6,),
            name="reset_points"
        )
        
        logger.info("✅ JobQueue برای گزارش هفتگی و ریست امتیازها راه‌اندازی شد.")
    else:
        logger.warning("⚠️ JobQueue در دسترس نیست! گزارش هفتگی و ریست امتیازها غیرفعال است.")

    print(f"""
✅ ربات EDIT 41 با موفقیت روشن شد

🤖 نام ربات: {BOT_USERNAME}
👤 مالک: @JENERAL_41
🔗 کانال: {CHANNEL_USERNAME}
📊 دیتابیس: {DATABASE_NAME}

⚙️ قابلیت‌های فعال:
✅ عضویت اجباری چندگانه
✅ پنل ادمین چندلایه
✅ آپلود ریمیکس (فقط کد و فایل)
✅ افزودن خودکار دکمه بعد از ثبت ریمیکس
✅ دکمه‌های 👍 و 👎
✅ ریمیکس‌های برتر
✅ ریمیکس تصادفی
✅ دریافت ریمیکس با کد
✅ پیشنهاد آهنگ برای ادیت
✅ دعوت دوستان
✅ سیستم امتیازدهی
✅ برترین‌های هفته
✅ گزارش هفتگی
✅ پنل آمار کامل
✅ بکاپ دستی
✅ پیام اخطار خروج از کانال
✅ تشخیص خودکار مالک
""")

    app.run_polling()


if __name__ == "__main__":
    main()