# utils.py
# توابع کمکی و ابزارها

import os
import re
from datetime import datetime
import tempfile
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TRCK, COMM
from PIL import Image
from config import BOT_USERNAME, CHANNEL_USERNAME

# خط جداکننده - فقط بین متن‌ها استفاده می‌شود
SEPARATOR = "•─┅━━━┅┅ ✦ ┅┅━━━┅─•"

def format_message(text, title=None):
    """قالب‌بندی حرفه‌ای پیام‌ها با خط جداکننده (فقط بین متن‌ها)"""
    if title:
        return f"{title}\n\n{SEPARATOR}\n\n{text}"
    return text

def format_message_with_separator(text1, text2):
    """دو متن با خط جداکننده بین آنها"""
    return f"{text1}\n\n{SEPARATOR}\n\n{text2}"

def create_cover_thumbnail(image_path):
    img = Image.open(image_path)
    if img.size[0] != img.size[1]:
        size = min(img.size)
        left = (img.size[0] - size) // 2
        top = (img.size[1] - size) // 2
        img = img.crop((left, top, left + size, top + size))
    
    temp_jpg = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    img.save(temp_jpg.name, "JPEG", quality=95, optimize=True)
    return temp_jpg.name

def add_metadata_to_mp3(mp3_path, cover_path, title, artist, code):
    try:
        audio = MP3(mp3_path, ID3=ID3)
        
        try:
            tags = ID3(mp3_path)
        except:
            tags = ID3()
        
        tags.add(TIT2(encoding=3, text=title))
        tags.add(TPE1(encoding=3, text=artist))
        tags.add(TRCK(encoding=3, text=str(code)))
        tags.add(COMM(encoding=3, lang='eng', desc='Bot', text=f"Remix Code: {code} | @{BOT_USERNAME.replace('@', '')}"))
        
        cover_thumb = create_cover_thumbnail(cover_path)
        with open(cover_thumb, 'rb') as img_file:
            tags.add(APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=img_file.read()
            ))
        
        os.unlink(cover_thumb)
        tags.save(mp3_path, v2_version=3)
        return True
    except Exception as e:
        print(f"Error adding metadata: {e}")
        return False

def create_remix_link(remix_code):
    return f"https://t.me/{BOT_USERNAME.replace('@', '')}?start=code_{remix_code}"

def create_referral_link(user_id):
    return f"https://t.me/{BOT_USERNAME.replace('@', '')}?start=ref_{user_id}"

def create_membership_keyboard(channels):
    keyboard = []
    for channel_id, channel_link, display_name in channels:
        if "t.me/" in channel_link or "telegram.me/" in channel_link:
            url = channel_link
        else:
            url = f"https://t.me/{channel_link.replace('@', '')}"
        keyboard.append([InlineKeyboardButton(f"🔰 {display_name}", url=url)])
    
    keyboard.append([InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")])
    return InlineKeyboardMarkup(keyboard)

def create_vote_keyboard(remix_code, user_id):
    from database import get_user_vote
    import sqlite3
    from config import DATABASE_NAME
    
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute("SELECT likes, dislikes FROM remixes WHERE code = ?", (remix_code,))
    result = c.fetchone()
    conn.close()
    
    likes = result[0] if result else 0
    dislikes = result[1] if result else 0
    
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

def create_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎲 ریمیکس تصادفی", callback_data="random_remix")],
        [InlineKeyboardButton("🏆 ریمیکس‌های برتر", callback_data="top_remixes")],
        [InlineKeyboardButton("📊 آمار ربات", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ===== کیبورد Reply برای مالک =====
def create_owner_keyboard():
    keyboard = [
        [KeyboardButton("ورود به پنل مالک 👑")],
        [KeyboardButton("ورود به پنل کاربر عادی 👤")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ===== کیبورد Reply برای پنل ادمین =====
def create_admin_keyboard():
    keyboard = [
        [KeyboardButton("افزودن ریمیکس جدید")],
        [KeyboardButton("ریمیکس‌های برتر")],
        [KeyboardButton("افزودن کانال عضویت")],
        [KeyboardButton("لیست کانال‌های عضویت")],
        [KeyboardButton("حذف کانال عضویت")],
        [KeyboardButton("افزودن ادمین")],
        [KeyboardButton("حذف ادمین")],
        [KeyboardButton("تنظیم نرخ تبلیغات")],
        [KeyboardButton("آمار کامل")],
        [KeyboardButton("بکاپ دیتابیس")],
        [KeyboardButton("تغییر رمز پنل")],
        [KeyboardButton("بستن پنل")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def check_user_in_channel(user_id, channel_link, bot):
    try:
        if "t.me/" in channel_link:
            chat_username = channel_link.split("t.me/")[-1].split("?")[0]
        else:
            chat_username = channel_link.replace("@", "")
        
        if not chat_username:
            return False
        
        chat_member = bot.get_chat_member(chat_id=f"@{chat_username}", user_id=user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Error checking membership: {e}")
        return False

def check_all_memberships(user_id, channels, bot):
    for channel_id, channel_link, display_name in channels:
        if not check_user_in_channel(user_id, channel_link, bot):
            return False, display_name
    return True, None

def extract_code_from_text(text):
    match = re.search(r'کد\s*[:：]\s*(\d+)', text)
    if match:
        return int(match.group(1))
    return None

def extract_number(text):
    """استخراج عدد از متن (حذف کاراکترهای غیرعددی)"""
    numbers = re.findall(r'\d+', text)
    if numbers:
        return int(numbers[0])
    return None

def get_persian_date():
    from datetime import datetime
    now = datetime.now()
    return now.strftime("%Y/%m/%d")

def format_remix_info(code, title, artist, views, likes, dislikes, created_at):
    date_str = created_at[:10] if created_at else "نامشخص"
    
    text = f"""🎵 {title}
🎤 خواننده: {artist}
🎚 کد: {code}
📅 تاریخ انتشار: {date_str}

{SEPARATOR}

👁 بازدید: {views}
👍 پسندیده: {likes}
👎 نپسندیده: {dislikes}"""
    return text

def is_admin_or_owner(user_id, owner_id):
    from database import is_admin
    return user_id == owner_id or is_admin(user_id)