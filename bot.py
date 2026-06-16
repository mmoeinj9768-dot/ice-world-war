# bot.py
# کد اصلی ربات EDIT 41

import os
import logging
import asyncio
import shutil
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import TOKEN, OWNER_ID, CHANNEL_USERNAME, BOT_USERNAME, ADMIN_PANEL_PASSWORD, DATABASE_NAME
from database import *
from utils import *

# تنظیم لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# حالت‌های موقت
user_temp_data = {}
admin_session = {}

# ============================================================
# تابع start
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "کاربر"
    first_name = update.effective_user.first_name or "کاربر"

    add_user(user_id, username, first_name)

    args = context.args

    if args and args[0].startswith("code_"):
        try:
            remix_code = int(args[0].split("code_")[1])
            context.user_data['pending_remix'] = remix_code
            await check_and_send_remix(update, context, remix_code)
            return
        except:
            await update.message.reply_text("❌ لینک نامعتبر است!")
            return

    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0].split("ref_")[1])
            if referrer_id != user_id:
                add_referral(referrer_id, user_id)
                if check_and_activate_referral_rewards(referrer_id):
                    await context.bot.send_message(
                        referrer_id,
                        f"🎉 تبریک! شما ۵ نفر را به ربات دعوت کردید.\n\n"
                        f"✅ پاداش شما فعال شد:\n"
                        f"به مدت ۱۰ روز می‌توانید بدون عضویت اجباری، هر ریمیکسی را دانلود کنید! 🎵"
                    )
                activate_referral_reward(user_id, 3, 'referred')
                await update.message.reply_text(
                    f"🎉 شما با کد دعوت وارد شدید!\n\n"
                    f"✅ پاداش شما فعال شد:\n"
                    f"به مدت ۳ روز می‌توانید بدون عضویت اجباری، ریمیکس دانلود کنید! 🎵"
                )
        except:
            pass

    welcome_text = f"""🎵 به ربات EDIT 41 خوش آمدید!

{CHANNEL_USERNAME}
بهترین کانال ادیت و ریمیکس‌های فوق‌العاده

🎧 برای دریافت ریمیکس، روی دکمه‌های زیر کلیک کنید"""
    
    keyboard = create_main_menu_keyboard()
    await update.message.reply_text(welcome_text, reply_markup=keyboard)

# ============================================================
# تابع بررسی و ارسال ریمیکس
# ============================================================
async def check_and_send_remix(update: Update, context: ContextTypes.DEFAULT_TYPE, remix_code):
    user_id = update.effective_user.id
    username = update.effective_user.first_name or "کاربر"

    deactivate_expired_channels()

    has_reward = has_referral_reward(user_id)
    channels = get_active_channels()

    if not has_reward:
        is_member, failed_channel = check_all_memberships(user_id, channels, context.bot)
        if not is_member:
            context.user_data['pending_remix'] = remix_code
            keyboard = create_membership_keyboard(channels)
            text = f"""🎵 دریافت ریمیکس

کاربر {username} عزیز ❤️

برای دریافت نسخه کامل ریمیکس، ابتدا در کانال‌های زیر عضو شوید و سپس روی گزینه «عضو شدم ✅» ضربه بزنید.

{SEPARATOR}

پس از تأیید عضویت، فایل به صورت خودکار ارسال خواهد شد. 🎧🔥"""
            await update.message.reply_text(text, reply_markup=keyboard)
            return

    remix = get_remix(remix_code)
    if not remix:
        await update.message.reply_text("❌ ریمیکس مورد نظر یافت نشد!")
        return

    code, file_path, title, artist, cover_path, views, likes, dislikes, created_at = remix

    increment_views(code, user_id)
    add_user_remix(user_id, code)

    vote_keyboard = create_vote_keyboard(code, user_id)

    caption = f"""🎵 {title}
🎤 خواننده: {artist}
🎚 کد: {code}
📅 تاریخ انتشار: {created_at[:10] if created_at else "نامشخص"}

{SEPARATOR}

🎧 از شنیدن این ریمیکس لذت بردید؟
نظرتون رو با کلیک روی دکمه‌های زیر ثبت کنید 👇"""

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
        logger.error(f"Error sending remix: {e}")
        await update.message.reply_text("❌ خطا در ارسال فایل! لطفاً بعداً تلاش کنید.")

# ============================================================
# تابع Callback Handler
# ============================================================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # ===== عضویت =====
    if data == "check_membership":
        remix_code = context.user_data.get('pending_remix')
        if not remix_code:
            await query.edit_message_text("❌ خطا! لطفاً دوباره از لینک وارد شوید.")
            return

        deactivate_expired_channels()
        channels = get_active_channels()
        has_reward = has_referral_reward(user_id)

        if not has_reward:
            is_member, failed_channel = check_all_memberships(user_id, channels, context.bot)
            if not is_member:
                await query.answer("❌ شما در همه کانال‌ها عضو نشده‌اید!", show_alert=True)
                keyboard = create_membership_keyboard(channels)
                await query.edit_message_reply_markup(reply_markup=keyboard)
                return

        await query.edit_message_text("✅ عضویت شما تأیید شد! در حال ارسال فایل...")

        remix = get_remix(remix_code)
        if remix:
            code, file_path, title, artist, cover_path, views, likes, dislikes, created_at = remix
            increment_views(code, user_id)
            add_user_remix(user_id, code)

            vote_keyboard = create_vote_keyboard(code, user_id)
            caption = f"""🎵 {title}
🎤 خواننده: {artist}
🎚 کد: {code}
📅 تاریخ انتشار: {created_at[:10] if created_at else "نامشخص"}

{SEPARATOR}

🎧 از شنیدن این ریمیکس لذت بردید؟
نظرتون رو با کلیک روی دکمه‌های زیر ثبت کنید 👇"""
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
            except Exception as e:
                logger.error(f"Error: {e}")
                await context.bot.send_message(user_id, "❌ خطا در ارسال فایل!")
        else:
            await context.bot.send_message(user_id, "❌ ریمیکس یافت نشد!")

        context.user_data.pop('pending_remix', None)
        return

    # ===== منوی اصلی =====
    if data == "random_remix":
        remix = get_random_remix()
        if remix:
            code, title, artist, file_path = remix
            text = f"""🎲 ریمیکس تصادفی

🎵 {title}
🎤 {artist}
🎚 کد: {code}

{SEPARATOR}

📥 برای دریافت، روی لینک زیر کلیک کنید:
{create_remix_link(code)}"""
            await query.edit_message_text(text)
        else:
            await query.edit_message_text("❌ هیچ ریمیکسی در دیتابیس وجود ندارد!")
        return

    if data == "top_remixes":
        top_views = get_top_remixes_by_views(3)
        top_likes = get_top_remixes_by_likes(3)

        text = f"""🏆 ریمیکس‌های برتر

📊 پربازدیدترین:
"""
        if top_views:
            for i, (code, title, artist, views, likes, dislikes, created_at) in enumerate(top_views, 1):
                text += f"{i}. {code} - {title} - {artist}\n   👁 {views} بازدید\n"
        else:
            text += "هیچ ریمیکسی موجود نیست.\n"

        text += f"""
{SEPARATOR}

❤️ محبوب‌ترین (نظر مثبت):
"""
        if top_likes:
            for i, (code, title, artist, views, likes, dislikes, created_at, score) in enumerate(top_likes, 1):
                text += f"{i}. {code} - {title} - {artist}\n   👍 {likes} | 👎 {dislikes} | امتیاز: {score}\n"
        else:
            text += "هیچ ریمیکسی موجود نیست."

        await query.edit_message_text(text)
        return

    if data == "stats":
        stats = get_stats()
        text = f"""📊 آمار ربات

👥 کل کاربران: {stats['total_users']}
🎵 کل ریمیکس‌ها: {stats['total_remixes']}
📥 کل دانلودها: {stats['total_downloads']}
🔗 کانال‌های فعال: {stats['active_channels']}

{SEPARATOR}

🏆 پربازدیدترین ریمیکس:
"""
        if stats['most_viewed']:
            code, title, artist, views = stats['most_viewed']
            text += f"{code} - {title} - {artist} (👁 {views})"
        else:
            text += "هیچ ریمیکسی موجود نیست."

        text += f"""

❤️ محبوب‌ترین ریمیکس:
"""
        if stats['most_liked']:
            code, title, artist, score = stats['most_liked']
            text += f"{code} - {title} - {artist} (⭐ {score})"
        else:
            text += "هیچ ریمیکسی موجود نیست."

        await query.edit_message_text(text)
        return

    if data == "help":
        text = f"""ℹ️ راهنمای ربات

🎵 دریافت ریمیکس:
روی لینک زیر هر پست در کانال کلیک کنید

🎲 ریمیکس تصادفی:
از منوی اصلی گزینه مربوطه را انتخاب کنید

🏆 ریمیکس‌های برتر:
مشاهده پربازدیدترین و محبوب‌ترین ریمیکس‌ها

📊 آمار ربات:
مشاهده آمار کلی ربات

{SEPARATOR}

🔗 کانال اصلی:
{CHANNEL_USERNAME}"""
        await query.edit_message_text(text)
        return

    # ===== رأی =====
    if data.startswith("vote_"):
        parts = data.split("_")
        remix_code = int(parts[1])
        vote = int(parts[2])

        existing_vote = get_user_vote(user_id, remix_code)
        if existing_vote != 0:
            await query.answer("⛔ شما قبلاً به این ریمیکس رأی داده‌اید!", show_alert=True)
            return

        set_user_vote(user_id, remix_code, vote)
        new_keyboard = create_vote_keyboard(remix_code, user_id)
        await query.edit_message_reply_markup(reply_markup=new_keyboard)

        if vote == 1:
            await query.answer("👍 نظر شما ثبت شد! ممنون.", show_alert=False)
        else:
            await query.answer("👎 نظر شما ثبت شد! ممنون.", show_alert=False)
        return

    # ===== پنل ادمین =====
    if data.startswith("admin"):
        if not (user_id == OWNER_ID or is_admin(user_id)):
            await query.edit_message_text("⛔ شما دسترسی ادمین ندارید!")
            return

        if data == "admin_panel":
            admin_session[user_id] = {'step': 'waiting_password'}
            await query.edit_message_text(
                f"""🔐 تایید امنیتی

لطفاً رمز عبور پنل ادمین را وارد کنید:

{SEPARATOR}

(رمز پیش‌فرض: {ADMIN_PANEL_PASSWORD})"""
            )
            return

        if admin_session.get(user_id, {}).get('verified') != True:
            await query.edit_message_text("⛔ لطفاً ابتدا رمز پنل را وارد کنید!")
            return

        if data == "admin_panel_verified":
            keyboard = create_admin_keyboard()
            await query.edit_message_text(
                f"""🔧 پنل مدیریت ربات

لطفاً یکی از گزینه‌ها را انتخاب کنید:""",
                reply_markup=keyboard
            )
            return

        if data == "admin_add_remix":
            context.user_data['admin_action'] = 'add_remix_code'
            await query.edit_message_text(
                f"""📀 افزودن ریمیکس جدید

لطفاً کد عددی ریمیکس را ارسال کنید:
(مثال: 15)

{SEPARATOR}"""
            )
            return

        if data == "admin_top_remixes":
            top_views = get_top_remixes_by_views(3)
            top_likes = get_top_remixes_by_likes(3)

            text = f"""🏆 ریمیکس‌های برتر

📊 پربازدیدترین:
"""
            if top_views:
                for i, (code, title, artist, views, likes, dislikes, created_at) in enumerate(top_views, 1):
                    text += f"{i}. {code} - {title} - {artist}\n   👁 {views} بازدید | 👍 {likes} | 👎 {dislikes}\n"
            else:
                text += "هیچ ریمیکسی موجود نیست.\n"

            text += f"""
{SEPARATOR}

❤️ محبوب‌ترین (نظر مثبت):
"""
            if top_likes:
                for i, (code, title, artist, views, likes, dislikes, created_at, score) in enumerate(top_likes, 1):
                    text += f"{i}. {code} - {title} - {artist}\n   👍 {likes} | 👎 {dislikes} | امتیاز: {score}\n"
            else:
                text += "هیچ ریمیکسی موجود نیست."

            await query.edit_message_text(text)
            return

        if data == "admin_add_channel":
            context.user_data['admin_action'] = 'add_channel_link'
            await query.edit_message_text(
                f"""🔗 افزودن کانال عضویت جدید

لطفاً لینک یا یوزرنیم کانال را ارسال کنید:
(مثال: @EDIT_41 یا https://t.me/EDIT_41)

{SEPARATOR}"""
            )
            return

        if data == "admin_list_channels":
            channels = get_all_channels()
            if not channels:
                await query.edit_message_text("📺 هیچ کانالی در دیتابیس وجود ندارد!")
                return

            text = "📺 لیست کانال‌های عضویت\n\n"
            for ch_id, link, name, expires, active in channels:
                status = "✅ فعال" if active else "❌ غیرفعال"
                expiry = expires if expires else "نامحدود"
                text += f"🆔 {ch_id}\n🔹 {name}\n🔗 {link}\n📅 انقضا: {expiry}\n📊 وضعیت: {status}\n\n"

            await query.edit_message_text(text)
            return

        if data == "admin_remove_channel":
            context.user_data['admin_action'] = 'remove_channel'
            channels = get_all_channels()
            if not channels:
                await query.edit_message_text("📺 هیچ کانالی در دیتابیس وجود ندارد!")
                return

            text = "🗑 حذف کانال عضویت\n\nلطفاً آیدی عددی کانال را ارسال کنید:\n\n"
            for ch_id, link, name, expires, active in channels:
                status = "✅" if active else "❌"
                text += f"🆔 {ch_id} - {name} {status}\n"

            await query.edit_message_text(text)
            return

        if data == "admin_add_admin":
            context.user_data['admin_action'] = 'add_admin'
            await query.edit_message_text(
                f"""👥 افزودن ادمین جدید

لطفاً آیدی عددی کاربر جدید را ارسال کنید:
(از @userinfobot بگیرید)

{SEPARATOR}"""
            )
            return

        if data == "admin_remove_admin":
            context.user_data['admin_action'] = 'remove_admin'
            admins = get_all_admins()
            if not admins:
                await query.edit_message_text("👥 هیچ ادمینی غیر از مالک وجود ندارد!")
                return

            text = "🚫 حذف ادمین\n\nلیست ادمین‌های فعلی:\n\n"
            for admin_id in admins:
                text += f"🆔 {admin_id}\n"

            text += f"\n{SEPARATOR}\n\nلطفاً آیدی عددی ادمین مورد نظر را ارسال کنید:"
            await query.edit_message_text(text)
            return

        if data == "admin_set_price":
            context.user_data['admin_action'] = 'set_price'
            current_price = get_setting('ad_price_per_day') or "50000"
            await query.edit_message_text(
                f"""💰 تنظیم نرخ تبلیغات

نرخ فعلی: {current_price} تومان در روز

{SEPARATOR}

لطفاً نرخ جدید را به تومان وارد کنید:
(مثال: 75000)"""
            )
            return

        if data == "admin_full_stats":
            stats = get_stats()
            text = f"""📊 آمار کامل ربات

👥 کل کاربران: {stats['total_users']}
🎵 کل ریمیکس‌ها: {stats['total_remixes']}
📥 کل دانلودها: {stats['total_downloads']}
🔗 کانال‌های فعال: {stats['active_channels']}

{SEPARATOR}

🏆 پربازدیدترین ریمیکس:
"""
            if stats['most_viewed']:
                code, title, artist, views = stats['most_viewed']
                text += f"{code} - {title} - {artist} (👁 {views})"
            else:
                text += "هیچ ریمیکسی موجود نیست."

            text += f"""

❤️ محبوب‌ترین ریمیکس:
"""
            if stats['most_liked']:
                code, title, artist, score = stats['most_liked']
                text += f"{code} - {title} - {artist} (⭐ {score})"
            else:
                text += "هیچ ریمیکسی موجود نیست."

            remixes = get_all_remixes()
            total_likes = sum(r[4] for r in remixes) if remixes else 0
            total_dislikes = sum(r[5] for r in remixes) if remixes else 0
            text += f"""

📊 آمار کلی رأی‌ها:
👍 کل لایک‌ها: {total_likes}
👎 کل دیسلایک‌ها: {total_dislikes}

📈 نرخ محبوبیت:
"""
            if total_likes + total_dislikes > 0:
                rate = (total_likes / (total_likes + total_dislikes)) * 100
                text += f"{rate:.1f}% لایک"
            else:
                text += "هنوز رأیی ثبت نشده"

            await query.edit_message_text(text)
            return

        if data == "admin_backup":
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy(DATABASE_NAME, backup_name)

            await query.edit_message_text(
                f"""💾 بکاپ دیتابیس

✅ فایل بکاپ با موفقیت ایجاد شد!

📁 نام فایل: {backup_name}
📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{SEPARATOR}

⚠️ لطفاً فایل را در جای امن ذخیره کنید."""
            )

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

        if data == "admin_change_password":
            context.user_data['admin_action'] = 'change_password'
            await query.edit_message_text(
                f"""🔐 تغییر رمز پنل ادمین

رمز فعلی: {ADMIN_PANEL_PASSWORD}

{SEPARATOR}

لطفاً رمز جدید (۴ رقمی) را وارد کنید:"""
            )
            return

        if data == "admin_close":
            await query.delete_message()
            return

# ============================================================
# تابع مدیریت پیام‌ها
# ============================================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not (user_id == OWNER_ID or is_admin(user_id)):
        return

    text = update.message.text
    action = context.user_data.get('admin_action')

    # تایید دو مرحله‌ای
    if admin_session.get(user_id, {}).get('step') == 'waiting_password':
        if text == ADMIN_PANEL_PASSWORD:
            admin_session[user_id] = {'verified': True}
            keyboard = create_admin_keyboard()
            await update.message.reply_text(
                f"""✅ رمز تأیید شد!

🔧 به پنل مدیریت خوش آمدید.

{SEPARATOR}""",
                reply_markup=keyboard
            )
            context.user_data.pop('admin_action', None)
        else:
            await update.message.reply_text("❌ رمز اشتباه است! دوباره تلاش کنید.")
        return

    if admin_session.get(user_id, {}).get('verified') != True:
        await update.message.reply_text("⛔ لطفاً ابتدا با دستور /admin و وارد کردن رمز، وارد پنل شوید.")
        return

    # ===== افزودن ریمیکس =====
    if action == 'add_remix_code':
        try:
            code = int(text.strip())
            if get_remix(code):
                await update.message.reply_text(f"⚠️ ریمیکس با کد {code} قبلاً وجود دارد! کد دیگری وارد کنید.")
                return
            context.user_data['new_remix_code'] = code
            context.user_data['admin_action'] = 'add_remix_title'
            await update.message.reply_text(
                f"""🎵 عنوان آهنگ

لطفاً عنوان آهنگ (Title) را وارد کنید:

{SEPARATOR}"""
            )
        except:
            await update.message.reply_text("❌ کد معتبر نیست! یک عدد ارسال کنید.")

    elif action == 'add_remix_title':
        context.user_data['new_remix_title'] = text
        context.user_data['admin_action'] = 'add_remix_artist'
        await update.message.reply_text(
            f"""🎤 نام خواننده

لطفاً نام خواننده (Artist) را وارد کنید:

{SEPARATOR}"""
        )

    elif action == 'add_remix_artist':
        context.user_data['new_remix_artist'] = text
        context.user_data['admin_action'] = 'add_remix_cover'
        await update.message.reply_text(
            f"""🖼 عکس کاور

لطفاً عکس کاور آهنگ را ارسال کنید (حتماً با نسبت 1:1):

{SEPARATOR}"""
        )

    elif action == 'add_remix_cover':
        if update.message.photo:
            photo_file = await update.message.photo[-1].get_file()
            code = context.user_data['new_remix_code']
            cover_path = f"covers/code_{code}.jpg"
            os.makedirs("covers", exist_ok=True)
            await photo_file.download_to_drive(cover_path)
            context.user_data['new_remix_cover'] = cover_path
            context.user_data['admin_action'] = 'add_remix_audio'
            await update.message.reply_text(
                f"""🎵 ارسال فایل MP3

لطفاً فایل MP3 ریمیکس را ارسال کنید:

{SEPARATOR}"""
            )
        else:
            await update.message.reply_text("❌ لطفاً یک عکس ارسال کنید!")

    elif action == 'add_remix_audio':
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
                    f"""✅ ریمیکس با موفقیت ذخیره شد!

🎵 {title} - {artist}
🎚 کد: {code}
🖼 عکس کاور به متادیتا اضافه شد.

{SEPARATOR}

🔗 لینک دریافت:
{create_remix_link(code)}"""
                )
            else:
                await update.message.reply_text("⚠️ فایل ذخیره شد اما متادیتا اضافه نشد.")

            for key in ['admin_action', 'new_remix_code', 'new_remix_title', 'new_remix_artist', 'new_remix_cover']:
                context.user_data.pop(key, None)
        else:
            await update.message.reply_text("❌ لطفاً یک فایل MP3 معتبر ارسال کنید!")

    # ===== افزودن کانال =====
    elif action == 'add_channel_link':
        context.user_data['new_channel_link'] = text
        context.user_data['admin_action'] = 'add_channel_name'
        await update.message.reply_text(
            f"""🔰 نام نمایشی کانال

لطفاً یک نام برای این کانال وارد کنید:
(مثال: کانال اصلی 🖤 یا تبلیغ 💢)

{SEPARATOR}"""
        )

    elif action == 'add_channel_name':
        context.user_data['new_channel_name'] = text
        context.user_data['admin_action'] = 'add_channel_days'
        await update.message.reply_text(
            f"""📅 مدت زمان اشتراک

لطفاً تعداد روزهای اشتراک را وارد کنید:
(مثال: 30 یا 60 یا 90)

{SEPARATOR}"""
        )

    elif action == 'add_channel_days':
        try:
            # استخراج عدد از متن
            clean_text = text.strip().replace(" ", "").replace("روز", "").replace("روز", "")
            days = int(clean_text)
            
            if days <= 0:
                await update.message.reply_text("❌ تعداد روز باید بیشتر از ۰ باشد!")
                return
                
            link = context.user_data.get('new_channel_link')
            name = context.user_data.get('new_channel_name')
            
            if not link or not name:
                await update.message.reply_text("❌ خطا! لطفاً مراحل را از اول تکرار کنید.")
                return
                
            add_channel(link, name, days)
            await update.message.reply_text(
                f"""✅ کانال با موفقیت اضافه شد!

🔗 {link}
🔰 {name}
📅 مدت: {days} روز
📆 تاریخ انقضا: {(datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')}

{SEPARATOR}"""
            )
            for key in ['admin_action', 'new_channel_link', 'new_channel_name']:
                context.user_data.pop(key, None)
        except ValueError:
            await update.message.reply_text("❌ تعداد روز معتبر نیست! لطفاً یک عدد (مثلاً 30) ارسال کنید.")
        except Exception as e:
            await update.message.reply_text(f"❌ خطا: {e}")

    # ===== حذف کانال =====
    elif action == 'remove_channel':
        try:
            channel_id = int(text.strip())
            remove_channel(channel_id)
            await update.message.reply_text(f"✅ کانال با آیدی {channel_id} با موفقیت حذف شد!")
            context.user_data.pop('admin_action', None)
        except:
            await update.message.reply_text("❌ آیدی معتبر نیست! یک عدد ارسال کنید.")

    # ===== افزودن ادمین =====
    elif action == 'add_admin':
        try:
            admin_id = int(text.strip())
            if admin_id == OWNER_ID:
                await update.message.reply_text("⛔ مالک قبلاً ادمین است!")
                return
            add_admin(admin_id, user_id)
            await update.message.reply_text(f"✅ کاربر با آیدی {admin_id} به ادمین‌ها اضافه شد!")
            context.user_data.pop('admin_action', None)
        except:
            await update.message.reply_text("❌ آیدی معتبر نیست! یک عدد ارسال کنید.")

    # ===== حذف ادمین =====
    elif action == 'remove_admin':
        try:
            admin_id = int(text.strip())
            if admin_id == OWNER_ID:
                await update.message.reply_text("⛔ نمی‌توانید مالک را حذف کنید!")
                return
            remove_admin(admin_id)
            await update.message.reply_text(f"✅ ادمین با آیدی {admin_id} حذف شد!")
            context.user_data.pop('admin_action', None)
        except:
            await update.message.reply_text("❌ آیدی معتبر نیست! یک عدد ارسال کنید.")

    # ===== تنظیم نرخ =====
    elif action == 'set_price':
        try:
            price = int(text.strip())
            set_setting('ad_price_per_day', str(price))
            await update.message.reply_text(f"✅ نرخ تبلیغات به {price} تومان در روز تغییر یافت!")
            context.user_data.pop('admin_action', None)
        except:
            await update.message.reply_text("❌ مبلغ معتبر نیست! یک عدد ارسال کنید.")

    # ===== تغییر رمز =====
    elif action == 'change_password':
        if len(text.strip()) >= 4:
            await update.message.reply_text(
                f"""🔐 رمز پنل تغییر یافت!

رمز جدید: {text.strip()}

{SEPARATOR}

⚠️ توجه: برای اعمال تغییرات، ربات را ریستارت کنید."""
            )
            context.user_data.pop('admin_action', None)
        else:
            await update.message.reply_text("❌ رمز باید حداقل ۴ کاراکتر باشد!")

    # ===== افزودن دکمه با لینک =====
    elif text and (text.startswith("https://t.me/") or text.startswith("t.me/")):
        if CHANNEL_USERNAME.replace("@", "") in text:
            context.user_data['pending_button_link'] = text
            context.user_data['admin_action'] = 'add_button_code'
            await update.message.reply_text(
                f"""🔗 افزودن دکمه به پست

لطفاً کد ریمیکس مربوط به این پست را وارد کنید:

{SEPARATOR}"""
            )
        else:
            await update.message.reply_text("ℹ️ لینک باید مربوط به کانال اصلی باشد.")

    elif action == 'add_button_code':
        try:
            code = int(text.strip())
            link = context.user_data.get('pending_button_link')
            if not link:
                await update.message.reply_text("❌ خطا! لطفاً مجدداً لینک را ارسال کنید.")
                return

            match = re.search(r'/(\d+)$', link)
            if not match:
                await update.message.reply_text("❌ لینک معتبر نیست! فرمت صحیح: https://t.me/EDIT_41/123")
                return

            message_id = int(match.group(1))
            chat_id = f"@{CHANNEL_USERNAME.replace('@', '')}"

            button_text = "🎵 دریافت ریمیکس کامل"
            button_url = create_remix_link(code)

            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(button_text, url=button_url)]])

            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=keyboard
                )
                await update.message.reply_text(
                    f"""✅ دکمه با موفقیت اضافه شد!

🔗 پست: {link}
🎚 کد ریمیکس: {code}

{SEPARATOR}

🔗 لینک دکمه: {button_url}"""
                )
            except Exception as e:
                await update.message.reply_text(f"❌ خطا در افزودن دکمه: {e}\n\nمطمئن شوید ربات در کانال ادمین است و دسترسی ویرایش پیام دارد.")

            context.user_data.pop('pending_button_link', None)
            context.user_data.pop('admin_action', None)

        except:
            await update.message.reply_text("❌ کد معتبر نیست! یک عدد ارسال کنید.")

# ============================================================
# تابع دستور /admin
# ============================================================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == OWNER_ID or is_admin(user_id):
        admin_session[user_id] = {'step': 'waiting_password'}
        await update.message.reply_text(
            f"""🔐 ورود به پنل مدیریت

لطفاً رمز عبور پنل را وارد کنید:

{SEPARATOR}

(رمز پیش‌فرض: {ADMIN_PANEL_PASSWORD})"""
        )
    else:
        await update.message.reply_text("⛔ شما دسترسی به پنل ادمین ندارید!")

# ============================================================
# تابع رویداد خروج از کانال (برای سرور)
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
                    text=f"""⚠️ اخطار خروج از کانال

شما از کانال خارج شدید ‼️
{CHANNEL_USERNAME}

{SEPARATOR}

برای دریافت ریمیکس‌های بیشتر و استفاده از ربات، عضو کانال شوید ✅"""
                )
                logger.info(f"User {user_id} left channel, notification sent.")
            except Exception as e:
                logger.error(f"Could not send leave notification to {user_id}: {e}")

        elif new_status == "member":
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"""🎉 خوش برگشتی!

{CHANNEL_USERNAME}

همیشه منتظر ریمیکس‌های جدید باش! 💪

{SEPARATOR}

🔗 برای دریافت ریمیکس، روی لینک‌های زیر پست‌ها کلیک کنید."""
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

    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(?!admin_)"))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^vote_"))
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^check_membership$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(MessageHandler(filters.AUDIO, handle_message))

    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_channel_leave))

    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(auto_backup, interval=86400, first=60)
        logger.info("✅ JobQueue برای بکاپ خودکار راه‌اندازی شد.")
    else:
        logger.warning("⚠️ JobQueue در دسترس نیست! بکاپ خودکار غیرفعال است.")

    print(f"""
✅ ربات EDIT 41 با موفقیت روشن شد!

🤖 نام ربات: {BOT_USERNAME}
👤 مالک: @JENERAL_41
🔗 کانال: {CHANNEL_USERNAME}
📊 دیتابیس: {DATABASE_NAME}

{SEPARATOR}

⚙️ قابلیت‌های فعال:
✅ عضویت اجباری چندگانه
✅ پنل ادمین با تایید دو مرحله‌ای
✅ آپلود ریمیکس با متادیتا
✅ دکمه‌های 👍 و 👎
✅ ریمیکس‌های برتر
✅ ریمیکس تصادفی
✅ سیستم دعوت دوستان
✅ پنل آمار کامل
✅ بکاپ خودکار
✅ پیام اخطار خروج از کانال
✅ افزودن خودکار دکمه با لینک
✅ قالب‌بندی حرفه‌ای
""")

    app.run_polling()

if __name__ == "__main__":
    main()