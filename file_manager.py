# utils/file_manager.py
# مدیریت فایل‌ها

import os
import uuid
from typing import Optional
from pathlib import Path
from config import REMIXES_PATH, COVERS_PATH, STORAGE_PATH
from utils.logger import get_logger

logger = get_logger(__name__)


# ===== ایجاد پوشه‌ها =====
def ensure_directories():
    """ایجاد پوشه‌های مورد نیاز"""
    os.makedirs(STORAGE_PATH, exist_ok=True)
    os.makedirs(REMIXES_PATH, exist_ok=True)
    os.makedirs(COVERS_PATH, exist_ok=True)
    logger.info("✅ Directories created")


def save_remix_file(file, code: int, ext: str) -> Optional[str]:
    """ذخیره فایل ریمیکس با بررسی None"""
    if file is None:
        logger.warning(f"⚠️ File is None for code {code}")
        return None
    
    try:
        unique_id = uuid.uuid4().hex[:8]
        filename = f"remix_{code}_{unique_id}.{ext}"
        
        if ext == "mp3":
            path = os.path.join(REMIXES_PATH, filename)
        else:
            path = os.path.join(COVERS_PATH, filename)
        
        file.download_to_drive(path)
        logger.info(f"✅ File saved: {path}")
        return path
    except Exception as e:
        logger.error(f"❌ Error saving file: {e}")
        return None


def delete_remix_file(path: str) -> bool:
    """حذف فایل ریمیکس"""
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"🗑️ File deleted: {path}")
            return True
        logger.warning(f"File not found: {path}")
        return False
    except Exception as e:
        logger.error(f"❌ Error deleting file {path}: {e}")
        return False


def get_file_size(path: str) -> int:
    """دریافت حجم فایل (بایت)"""
    try:
        return os.path.getsize(path)
    except:
        return 0


def file_exists(path: str) -> bool:
    """بررسی وجود فایل"""
    return os.path.exists(path)


def get_file_info(path: str) -> dict:
    """دریافت اطلاعات کامل فایل"""
    try:
        stat = os.stat(path)
        return {
            "exists": True,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime
        }
    except:
        return {"exists": False}