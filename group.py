# handlers/group.py
# هندلرهای گروه خصوصی

from telegram import Update
from telegram.ext import ContextTypes
from config import OWNER_ID, CHANNEL_USERNAME, REQUEST_COOLDOWN_DAYS
import re


async def handle_group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های گروه خصوصی (پاسخ به درخواست‌ها)"""
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