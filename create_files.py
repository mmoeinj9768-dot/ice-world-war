# create_files.py
# ایجاد فایل‌های .env و .gitignore

import os

# محتوای فایل .env
env_content = """TOKEN=8940814486:AAFkx_Nl-_lMyxFsj4xIhPxzTW_ajLFBDRo
OWNER_ID=7700419184
BOT_USERNAME=@EDIT_41_BOT
CHANNEL_USERNAME=@EDIT_41
DATABASE_URL=sqlite:///bot.db
REQUEST_GROUP_ID=-1004434170476
REQUEST_COOLDOWN_DAYS=3
ADMIN_PANEL_PASSWORD=9729
RATE_LIMIT_PER_USER=30
STORAGE_PATH=storage
LOG_LEVEL=INFO
LOG_FILE=bot.log
WEEKLY_REPORT_HOUR=9
WEEKLY_REPORT_MINUTE=0
RESET_POINTS_HOUR=0
RESET_POINTS_MINUTE=0
READ_TIMEOUT=30
WRITE_TIMEOUT=30
CONNECT_TIMEOUT=30
POOL_TIMEOUT=30
"""

# محتوای فایل .gitignore
gitignore_content = """.env
*.db
__pycache__/
*.pyc
storage/
logs/
*.log
.DS_Store
.idea/
.vscode/
*.swp
*.bak
"""

# ایجاد فایل‌ها
with open(".env", "w") as f:
    f.write(env_content)
    print("✅ .env created")

with open(".gitignore", "w") as f:
    f.write(gitignore_content)
    print("✅ .gitignore created")

print("✅ All files created successfully!")