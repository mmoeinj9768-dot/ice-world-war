from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8843735484:AAE_aljnuOE18YdcYfv8Qxaej-jj4SSBKGk"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ربات فعال است ✅")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

print("BOT RUNNING")
app.run_polling()