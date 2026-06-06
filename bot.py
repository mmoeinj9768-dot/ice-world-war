from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8040212612:AAFZtwqyYVfc0vBjCHHnGmSHv8h_osYOnNY"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 به ICE WORLD WAR خوش آمدید!\n\n"
        "برای مشاهده دستورات از /help استفاده کنید."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "برای دسترسی به تمامی توضیحات میتوانید در کانال زیر عضو شوید ‼️\n"
        "@ICE_WORLD_INFO\n\n"
        "اگر سوالی برای شما پیش آمد و جوابش را در این کانال پیدا نکردید، می توانید با پشتیبانی ارتباط برقرار کنید ✅"
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ادمین پشتیبانی 👤\n"
        "🆔 @JENERAL_41"
    )

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("support", support))

print("ICE WORLD WAR Bot Started...")
app.run_polling()