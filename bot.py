import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8040212612:AAFZtwqyYVfc0vBjCHHnGmSHv8h_osYOnNY"

logging.basicConfig(level=logging.INFO)

# ---------------- DATA ----------------
users = {}

def get_user(user):
    uid = str(user.id)
    if uid not in users:
        users[uid] = {
            "name": user.first_name,
            "username": user.username,
            "country": None,
            "budget": 0,
            "income": 5_000_000,
            "happiness": 100,
        }
    return users[uid]

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user)

    keyboard = [
        [InlineKeyboardButton("🌍 انتخاب کشور", callback_data="selection")],
        [InlineKeyboardButton("💰 پروفایل", callback_data="profile")],
        [InlineKeyboardButton("🏪 بازار", callback_data="market")]
    ]

    await update.message.reply_text(
        "🌍 ICE WORLD WAR BOT\nیکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- CALLBACK ----------------
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = get_user(query.from_user)
    data = query.data

    # ---------------- SELECTION ----------------
    if data == "selection":
        keyboard = [
            [InlineKeyboardButton("USA | آمریکا", callback_data="set_country_USA")],
            [InlineKeyboardButton("RUSSIA | روسیه", callback_data="set_country_RUSSIA")],
            [InlineKeyboardButton("CHINA | چین", callback_data="set_country_CHINA")],
            [InlineKeyboardButton("FRANCE | فرانسه", callback_data="set_country_FRANCE")]
        ]
        await query.edit_message_text(
            "🌍 کشور خود را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ---------------- SET COUNTRY ----------------
    if data.startswith("set_country_"):
        country = data.split("_")[2]
        user["country"] = country
        await query.edit_message_text(f"✅ کشور انتخاب شد: {country}")

    # ---------------- PROFILE ----------------
    if data == "profile":
        text = f"""
👤 پروفایل

نام: {user['name']}
آیدی: @{user['username']}

کشور: {user['country']}

💰 بودجه: {user['budget']}
📈 درآمد: {user['income']}
📊 رضایت: {user['happiness']}
"""
        await query.edit_message_text(text)

    # ---------------- MARKET ----------------
    if data == "market":
        keyboard = [
            [InlineKeyboardButton("⚔️ تجهیزات نظامی", callback_data="military")],
            [InlineKeyboardButton("💸 تجهیزات اقتصادی", callback_data="eco")]
        ]
        await query.edit_message_text(
            "🏪 بازار",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ---------------- ECONOMY ----------------
    if data == "eco":
        keyboard = [
            [InlineKeyboardButton("🖨 دستگاه چاپ پول", callback_data="printer")],
            [InlineKeyboardButton("🏭 رضایت مردم", callback_data="happiness")]
        ]
        await query.edit_message_text(
            "💸 اقتصادی",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ---------------- PRINTER ----------------
    if data == "printer":
        keyboard = [
            [InlineKeyboardButton("سطح 1 - 5M", callback_data="buy_p1")],
            [InlineKeyboardButton("سطح 2 - 10M", callback_data="buy_p2")],
            [InlineKeyboardButton("سطح 3 - 15M", callback_data="buy_p3")],
            [InlineKeyboardButton("سطح 4 - 15M", callback_data="buy_p4")]
        ]
        await query.edit_message_text("🖨 انتخاب دستگاه:", reply_markup=InlineKeyboardMarkup(keyboard))

    # ---------------- BUY PRINTER ----------------
    if data.startswith("buy_p"):
        level = int(data[-1])
        prices = {1: 5_000_000, 2: 10_000_000, 3: 15_000_000, 4: 15_000_000}
        income = {1: 2_500_000, 2: 5_000_000, 3: 7_500_000, 4: 10_000_000}

        price = prices[level]

        if user["budget"] >= price:
            user["budget"] -= price
            user["income"] += income[level]
            await query.edit_message_text("✅ خرید موفق انجام شد")
        else:
            await query.edit_message_text("❌ بودجه کافی نیست")

    # ---------------- HAPPINESS ----------------
    if data == "happiness":
        keyboard = [
            [InlineKeyboardButton("🏭 کارخانه", callback_data="h_factory")],
            [InlineKeyboardButton("🏡 خانه", callback_data="h_house")],
            [InlineKeyboardButton("🚗 ماشین", callback_data="h_car")]
        ]
        await query.edit_message_text("📊 افزایش رضایت:", reply_markup=InlineKeyboardMarkup(keyboard))

    if data == "h_factory":
        if user["budget"] >= 2_000_000:
            user["budget"] -= 2_000_000
            user["happiness"] += 20
            await query.edit_message_text("✅ کارخانه خریداری شد")
        else:
            await query.edit_message_text("❌ پول کافی نیست")

    if data == "h_house":
        if user["budget"] >= 1_000_000:
            user["budget"] -= 1_000_000
            user["happiness"] += 10
            await query.edit_message_text("✅ خانه خریداری شد")
        else:
            await query.edit_message_text("❌ پول کافی نیست")

    if data == "h_car":
        if user["budget"] >= 500_000:
            user["budget"] -= 500_000
            user["happiness"] += 5
            await query.edit_message_text("✅ ماشین خریداری شد")
        else:
            await query.edit_message_text("❌ پول کافی نیست")

# ---------------- TEXT INPUT ----------------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user)

    if update.message.text.isdigit():
        pass  # فعلاً برای نسخه آزمایشی ساده نگه داشتیم

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("ICE WORLD WAR Bot Started...")
    app.run_polling()

if __name__ == "__main__":
    main()