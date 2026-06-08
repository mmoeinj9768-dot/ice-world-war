import sqlite3
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================
TOKEN = "8848184643:AAFdHUjRZ82GgbWAw5YHxEkGQKjUDNM3UFM"
ADMIN_ID = 7700419184

# ================= DATABASE =================
db = sqlite3.connect("service.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS tickets(
    user_id INTEGER,
    message TEXT
)
""")
db.commit()

# ================= START MENU =================
def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("📌 سوال یا پیشنهاد", callback_data="support"),
            InlineKeyboardButton("🔗 کانال ها", callback_data="channels")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_button():
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 به ATR SERVICE خوش آمدید\n\nیکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=main_menu()
    )

# ================= BUTTON HANDLER =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # ================= CHANNELS =================
    if query.data == "channels":
        await query.edit_message_text(
            "🔗 کانال‌های رسمی ATR:\n\n"
            "📢 @ATR_NETWORK\n"
            "⚙ @ATR_COMMANDS",
            reply_markup=back_button()
        )

    # ================= SUPPORT =================
    elif query.data == "support":
        await query.edit_message_text(
            "📌 لطفاً پیام خود را ارسال کنید:\n\n"
            "✉ سوال یا پیشنهاد خود را بنویسید.",
            reply_markup=back_button()
        )

    # ================= BACK =================
    elif query.data == "back":
        await query.edit_message_text(
            "🤖 به ATR SERVICE خوش آمدید\n\nیکی از گزینه‌ها را انتخاب کنید:",
            reply_markup=main_menu()
        )

# ================= USER MESSAGE =================
async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    text = update.message.text

    # ذخیره پیام
    cur.execute(
        "INSERT INTO tickets(user_id, message) VALUES (?, ?)",
        (user.id, text)
    )
    db.commit()

    # ارسال به ادمین
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"""
📩 پیام جدید

👤 نام: {user.full_name}
🆔 آیدی: {user.id}

💬 پیام:
{text}

-------------------------
برای پاسخ:
/reply {user.id} پاسخ شما
"""
    )

    await update.message.reply_text(
        "✅ پیام شما ارسال شد و در حال بررسی است."
    )

# ================= REPLY SYSTEM =================
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    try:
        user_id = int(context.args[0])
        text = " ".join(context.args[1:])

        await context.bot.send_message(
            chat_id=user_id,
            text=f"📬 پاسخ پشتیبانی:\n\n{text}"
        )

        await update.message.reply_text("✅ ارسال شد")

    except:
        await update.message.reply_text(
            "❌ فرمت اشتباه\n\nمثال:\n/reply 123456 سلام"
        )

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reply", reply))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_message))

    print("🤖 ATR SERVICE RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()