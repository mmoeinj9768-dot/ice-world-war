# handlers/callback.py
# هندلرهای Callback (دکمه‌های شیشه‌ای)

from telegram import Update
from telegram.ext import ContextTypes
from services.remix_service import *
from services.membership_service import *
from services.points_service import *
from database.channel_repo import get_active_channels, deactivate_expired_channels
from database.user_repo import add_user_remix
from database.vote_repo import set_user_vote, get_user_vote
from database.db import get_pending_remix, clear_pending_remix
from core.middleware import log_request
from utils.cache import CacheManager
from utils.security import is_admin_or_owner


@log_request
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت تمام Callbackها"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    # ===== دکمه «عضو شدم ✅» =====
    if data == "check_membership":
        await handle_check_membership(update, context)
        return
    
    # ===== دکمه‌های رأی =====
    if data.startswith("vote_"):
        await handle_vote(update, context)
        return


async def handle_check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش دکمه «عضو شدم ✅»"""
    query = update.callback_query
    user_id = query.from_user.id
    
    remix_code = get_pending_remix(user_id)
    if not remix_code:
        await query.edit_message_text(
            "❌ کد ریمیکس پیدا نشد.\n\n"
            "لطفاً کد عددی ریمیکس مورد نظر را وارد کنید:"
        )
        context.user_data['user_action'] = 'get_remix_by_code'
        return
    
    deactivate_expired_channels()
    channels = get_active_channels()
    has_reward = has_referral_reward(user_id)
    
    is_member = True
    if not has_reward:
        is_member, failed_channel = check_all_memberships(user_id, context.bot)
    
    if not is_member:
        await query.answer("❌ در همه کانال‌ها عضو نشده‌اید!", show_alert=True)
        from handlers.user import create_membership_keyboard
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
        
        from handlers.user import create_vote_keyboard
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
        except Exception as e:
            await context.bot.send_message(user_id, "خطا در ارسال فایل ❌")
    else:
        await context.bot.send_message(user_id, "ریمیکس یافت نشد ❌")
    
    clear_pending_remix(user_id)


async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش دکمه‌های رأی"""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    parts = data.split("_")
    remix_code = int(parts[1])
    vote = int(parts[2])
    
    existing_vote = get_user_vote(user_id, remix_code)
    if existing_vote is not None and existing_vote != 0:
        await query.answer("شما قبلاً به این ریمیکس رأی داده‌اید ⛔", show_alert=True)
        return
    
    set_user_vote(user_id, remix_code, vote)
    from handlers.user import create_vote_keyboard
    new_keyboard = create_vote_keyboard(remix_code, user_id)
    await query.edit_message_reply_markup(reply_markup=new_keyboard)
    
    if vote == 1:
        await query.answer("نظر شما ثبت شد 👍 ممنون", show_alert=False)
    else:
        await query.answer("نظر شما ثبت شد 👎 ممنون", show_alert=False)