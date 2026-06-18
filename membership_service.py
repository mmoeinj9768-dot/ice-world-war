# services/membership_service.py
# سرویس عضویت اجباری

from database.channel_repo import get_active_channels
from utils.cache import CacheManager
from typing import List, Tuple
from telegram import Bot
from utils.logger import get_logger

logger = get_logger(__name__)


def check_user_in_channel(user_id: int, channel_link: str, chat_id: str, bot: Bot) -> bool:
    """بررسی عضویت کاربر در یک کانال با کش"""
    cache_key = f"membership_{user_id}_{chat_id or channel_link}"
    
    # بررسی کش
    cached = CacheManager.get(cache_key)
    if cached is not None:
        return cached
    
    try:
        if chat_id:
            identifier = chat_id
        else:
            if "t.me/" in channel_link:
                username = channel_link.split("t.me/")[-1].split("?")[0]
            else:
                username = channel_link.replace("@", "")
            identifier = f"@{username}"
        
        member = bot.get_chat_member(chat_id=identifier, user_id=user_id)
        result = member.status in ["member", "administrator", "creator"]
        
        # ذخیره در کش
        CacheManager.set(cache_key, result, ttl=60)
        return result
        
    except Exception as e:
        logger.error(f"❌ Membership check error: {e}")
        return False


def check_all_memberships(user_id: int, bot: Bot) -> tuple:
    """بررسی عضویت کاربر در همه کانال‌ها"""
    channels = get_active_channels()
    
    for channel_id, channel_link, chat_id, display_name in channels:
        if not check_user_in_channel(user_id, channel_link, chat_id, bot):
            return False, display_name
    
    return True, None


def get_required_channels() -> List[Tuple]:
    """دریافت لیست کانال‌های عضویت اجباری"""
    return get_active_channels()


def create_membership_keyboard(channels):
    """ساخت دکمه‌های عضویت اجباری"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = []
    for channel_id, channel_link, chat_id, display_name in channels:
        keyboard.append([InlineKeyboardButton(f"عضویت {display_name} 🔰", url=channel_link)])
    
    keyboard.append([InlineKeyboardButton("عضو شدم ✅", callback_data="check_membership")])
    return InlineKeyboardMarkup(keyboard)


def create_vote_keyboard(remix_code: int, user_id: int):
    """ساخت دکمه‌های رأی"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
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