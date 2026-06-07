import sqlite3
import logging
import asyncio
import random

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ================= CONFIG =================

BOT_TOKEN = "8040212612:AAFZtwqyYVfc0vBjCHHnGmSHv8h_osYOnNY"

ADMIN_USERNAME = "JENERAL_41"

CHANNEL_WAR = "@ICE_WORLD_WAR"
CHANNEL_ASSETS = "@ICE_WORLD_ASSETS"
CHANNEL_MARKET = "@ICE_WORLD_MARKET"

COUNTRIES = ["USA", "FRANCE", "CHINA", "RUSSIA"]
GROUPS = ["ISIS"]

DAILY_INCOME = 5_000_000

# ================= LOG =================

logging.basicConfig(level=logging.INFO)

# ================= DATABASE =================

conn = sqlite3.connect("ice_world.db", check_same_thread=False)
cur = conn.cursor()

def init_db():

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        country TEXT,
        group_name TEXT,
        balance INTEGER DEFAULT 0,
        happiness INTEGER DEFAULT 100,
        inflation INTEGER DEFAULT 0
    )
    """)

    # INVENTORY
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        user_id INTEGER,
        item TEXT
    )
    """)

    # WARS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS wars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker TEXT,
        defender TEXT,
        result TEXT
    )
    """)

    # 🌍 BORDERS DATABASE (NEW CORE SYSTEM)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS borders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_a TEXT,
        country_b TEXT,
        type TEXT
    )
    """)

    conn.commit()

    seed_borders()

# ================= BORDER SEED DATA =================

def seed_borders():

    cur.execute("SELECT COUNT(*) FROM borders")
    if cur.fetchone()[0] > 0:
        return

    borders = [
        ("USA", "CANADA", "LAND"),
        ("USA", "MEXICO", "LAND"),
        ("USA", "RUSSIA", "SEA"),

        ("FRANCE", "GERMANY", "LAND"),
        ("FRANCE", "UK", "SEA"),

        ("CHINA", "RUSSIA", "LAND"),
        ("CHINA", "JAPAN", "SEA"),

        ("RUSSIA", "USA", "SEA"),
        ("RUSSIA", "CHINA", "LAND")
    ]

    for a, b, t in borders:
        cur.execute("""
        INSERT INTO borders (country_a, country_b, type)
        VALUES (?,?,?)
        """, (a, b, t))

    conn.commit()

# ================= USERS =================

def create_user(uid, username):
    cur.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)",
                (uid, username))
    conn.commit()

def set_country(uid, country):
    cur.execute("UPDATE users SET country=? WHERE user_id=?",
                (country, uid))
    conn.commit()

def set_group(uid, group):
    cur.execute("UPDATE users SET group_name=? WHERE user_id=?",
                (group, uid))
    conn.commit()

# ================= BORDERS LOGIC =================

def has_land_route(a, b):

    cur.execute("""
    SELECT * FROM borders
    WHERE ((country_a=? AND country_b=?) OR (country_a=? AND country_b=?))
    AND type='LAND'
    """, (a, b, b, a))

    return cur.fetchone() is not None


def has_sea_route(a, b):

    cur.execute("""
    SELECT * FROM borders
    WHERE ((country_a=? AND country_b=?) OR (country_a=? AND country_b=?))
    AND type='SEA'
    """, (a, b, b, a))

    return cur.fetchone() is not None

# ================= ECONOMY =================

def add_income():
    cur.execute("UPDATE users SET balance = balance + ?", (DAILY_INCOME,))
    conn.commit()

# ================= WAR ENGINE =================

def calculate_power():

    attack = random.randint(50, 200)
    defense = random.randint(50, 200)

    return attack, defense


def resolve_war(attacker_country, defender_country, transport):

    atk, defn = calculate_power()

    # BORDER RULE CHECK
    if transport == "LAND":
        if not has_land_route(attacker_country, defender_country):
            return "NO_LAND_ROUTE"

    if transport == "SEA":
        if not has_sea_route(attacker_country, defender_country):
            return "NO_SEA_ROUTE"

    if atk > defn:
        return "ATTACKER_WINS"
    elif defn > atk:
        return "DEFENDER_WINS"

    return "DRAW"

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    create_user(user.id, user.username)

    keyboard = [
        ["🌍 انتخاب کشور"],
        ["⚔️ انتخاب گروهک"],
        ["📊 دارایی من"]
    ]

    await update.message.reply_text(
        "🔥 ICE WORLD WAR FINAL VERSION",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= HANDLE =================

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text
    user = update.effective_user

    create_user(user.id, user.username)

    if text in COUNTRIES:
        set_country(user.id, text)
        await update.message.reply_text(f"✅ کشور ثبت شد: {text}")

    elif text in GROUPS:
        set_group(user.id, text)
        await update.message.reply_text(f"⚔️ گروهک ثبت شد: {text}")

    elif text == "📊 دارایی من":

        cur.execute("""
        SELECT country, group_name, balance, happiness, inflation
        FROM users WHERE user_id=?
        """, (user.id,))

        u = cur.fetchone()

        if u:
            await update.message.reply_text(f"""
🌍 کشور: {u[0]}
⚔️ گروهک: {u[1]}
💰 پول: {u[2]}
😊 رضایت: {u[3]}%
📈 تورم: {u[4]}%
""")

# ================= ADMIN =================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.username != ADMIN_USERNAME:
        return

    keyboard = [
        [InlineKeyboardButton("📢 NEWS", callback_data="news")],
        [InlineKeyboardButton("⚖️ UN", callback_data="un")],
        [InlineKeyboardButton("💰 INCOME", callback_data="income")],
        [InlineKeyboardButton("⚔️ WAR TEST", callback_data="war")]
    ]

    await update.message.reply_text(
        "👑 FINAL ADMIN PANEL",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    if q.data == "income":
        add_income()
        await q.edit_message_text("💰 INCOME ADDED")

    elif q.data == "war":

        result = resolve_war("USA", "FRANCE", "LAND")

        await q.edit_message_text(f"""
⚔️ WAR RESULT TEST

USA vs FRANCE
Transport: LAND

RESULT: {result}
""")

# ================= MAIN =================

def main():

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(admin_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🚀 ICE WORLD FINAL SYSTEM RUNNING")

    app.run_polling()

if __name__ == "__main__":
    main()
