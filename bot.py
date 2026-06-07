import sqlite3
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= BOT TOKEN =================

BOT_TOKEN = "8040212612:AAFZtwqyYVfc0vBjCHHnGmSHv8h_osYOnNY"

# ================= DATABASE =================

conn = sqlite3.connect("ice_world.db", check_same_thread=False)
cur = conn.cursor()

# ================= FULL DATA =================

COUNTRIES = {
"USA": "آمریکا",
"CHINA": "چین",
"RUSSIA": "روسیه",
"FRANCE": "فرانسه",
"UK": "انگلیس",
"GERMANY": "آلمان",
"IRAN": "ایران",
"INDIA": "هند",
"JAPAN": "ژاپن",
"CANADA": "کانادا"
}

GROUPS = [
"FBI | اف بی آی",
"CIA | سی آی اِی",
"SEPAH | سپاه",
"FATEMIYOUN | فاطمیون",
"DARK | دارک وب",
"PENTAGON | پنتاگون",
"MOSSAD | موساد",
"YAKUZA | یاکوزا",
"ISIS | داعش"
]

EQUIPMENT = {
"F35": {"price": 9000000, "atk": 140, "def": 60},
"SU57": {"price": 8500000, "atk": 150, "def": 55},
"S400": {"price": 12000000, "atk": 0, "def": 260},
"T90": {"price": 3500000, "atk": 85, "def": 75},
"CRUISE": {"price": 5000000, "atk": 130, "def": 0},
"CYBER_TEAM": {"price": 2500000, "atk": 0, "def": 300}
}

BORDERS = {
("USA", "CANADA"): "LAND",
("USA", "MEXICO"): "LAND",
("USA", "RUSSIA"): "SEA",
("IRAN", "TURKEY"): "LAND",
("CHINA", "INDIA"): "LAND",
("FRANCE", "UK"): "SEA"
}

# ================= INIT DB =================

def init_db():

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        country TEXT DEFAULT 'NONE',
        group_name TEXT DEFAULT 'NONE',
        balance INTEGER DEFAULT 10000000
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        user_id INTEGER,
        item TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS borders (
        a TEXT,
        b TEXT,
        type TEXT
    )
    """)

    conn.commit()

    load_borders()

# ================= LOAD DATA INTO DB =================

def load_borders():

    cur.execute("SELECT COUNT(*) FROM borders")
    if cur.fetchone()[0] > 0:
        return

    for (a, b), t in BORDERS.items():
        cur.execute("INSERT INTO borders VALUES (?,?,?)", (a, b, t))

    conn.commit()

# ================= USER =================

def create_user(uid, username):
    cur.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)",
                (uid, username))
    conn.commit()

def get_inventory(uid):
    cur.execute("SELECT item FROM inventory WHERE user_id=?", (uid,))
    return [i[0] for i in cur.fetchall()]

def add_item(uid, item):
    cur.execute("INSERT INTO inventory VALUES (?,?)", (uid, item))
    conn.commit()

# ================= POWER =================

def power(items):

    atk = 0
    dfn = 0

    for i in items:
        if i in EQUIPMENT:
            atk += EQUIPMENT[i]["atk"]
            dfn += EQUIPMENT[i]["def"]

    return atk, dfn

# ================= CHECK BORDER =================

def can_attack(a, b):

    cur.execute("""
    SELECT type FROM borders
    WHERE (a=? AND b=?) OR (a=? AND b=?)
    """, (a, b, b, a))

    r = cur.fetchone()

    if not r:
        return False, None

    return True, r[0]

# ================= UI =================

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 پروفایل", callback_data="profile")],
        [InlineKeyboardButton("🌍 کشور", callback_data="country")],
        [InlineKeyboardButton("⚔️ گروهک", callback_data="group")],
        [InlineKeyboardButton("🛒 بازار", callback_data="market")],
        [InlineKeyboardButton("⚔️ جنگ", callback_data="war")]
    ])

def back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]
    ])

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    create_user(user.id, user.username)

    await update.message.reply_text(
        "🌍 ICE WORLD WAR FINAL SYSTEM",
        reply_markup=menu()
    )

# ================= CALLBACK =================

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    user = q.from_user
    create_user(user.id, user.username)

    d = q.data

    # HOME
    if d == "home":
        await q.edit_message_text("🏠 منو اصلی", reply_markup=menu())

    # PROFILE
    elif d == "profile":

        cur.execute("SELECT country, group_name, balance FROM users WHERE user_id=?",
                    (user.id,))
        u = cur.fetchone()

        inv = get_inventory(user.id)

        await q.edit_message_text(f"""
📊 پروفایل

🌍 کشور: {u[0]}
⚔️ گروهک: {u[1]}
💰 پول: {u[2]}

🧰 تجهیزات:
{", ".join(inv) if inv else "خالی"}
""", reply_markup=back())

    # COUNTRY
    elif d == "country":

        btn = [[InlineKeyboardButton(f"{k} | {v}", callback_data=f"setc_{k}")]
               for k, v in COUNTRIES.items()]

        btn.append([InlineKeyboardButton("🔙 بازگشت", callback_data="home")])

        await q.edit_message_text("🌍 انتخاب کشور", reply_markup=InlineKeyboardMarkup(btn))

    elif d.startswith("setc_"):

        c = d.replace("setc_", "")
        cur.execute("UPDATE users SET country=? WHERE user_id=?", (c, user.id))
        conn.commit()

        await q.edit_message_text("✅ کشور ثبت شد", reply_markup=back())

    # GROUP
    elif d == "group":

        btn = [[InlineKeyboardButton(g, callback_data=f"setg_{g.split('|')[0]}")]
               for g in GROUPS]

        btn.append([InlineKeyboardButton("🔙 بازگشت", callback_data="home")])

        await q.edit_message_text("⚔️ انتخاب گروهک", reply_markup=InlineKeyboardMarkup(btn))

    elif d.startswith("setg_"):

        g = d.replace("setg_", "")
        cur.execute("UPDATE users SET group_name=? WHERE user_id=?", (g, user.id))
        conn.commit()

        await q.edit_message_text("⚔️ گروهک ثبت شد", reply_markup=back())

    # MARKET
    elif d == "market":

        btn = [[InlineKeyboardButton(f"{k} - {v['price']}", callback_data=f"buy_{k}")]
               for k, v in EQUIPMENT.items()]

        btn.append([InlineKeyboardButton("🔙 بازگشت", callback_data="home")])

        await q.edit_message_text("🛒 بازار", reply_markup=InlineKeyboardMarkup(btn))

    elif d.startswith("buy_"):

        item = d.replace("buy_", "")
        price = EQUIPMENT[item]["price"]

        cur.execute("SELECT balance FROM users WHERE user_id=?", (user.id,))
        bal = cur.fetchone()[0]

        if bal < price:
            await q.edit_message_text("❌ پول کافی نیست", reply_markup=back())
            return

        cur.execute("UPDATE users SET balance = balance - ? WHERE user_id=?",
                    (price, user.id))

        add_item(user.id, item)

        await q.edit_message_text(f"✅ خرید شد: {item}", reply_markup=back())

    # WAR
    elif d == "war":

        cur.execute("SELECT country FROM users WHERE user_id=?", (user.id,))
        row = cur.fetchone()

        if not row:
            await q.edit_message_text("❌ کشور انتخاب نشده", reply_markup=back())
            return

        my_country = row[0]
        enemy = random.choice(list(COUNTRIES.keys()))

        ok, border_type = can_attack(my_country, enemy)

        if not ok:
            await q.edit_message_text("⛔ مرز بین کشورها وجود ندارد", reply_markup=back())
            return

        items = get_inventory(user.id)
        atk, dfn = power(items)

        enemy_atk = random.randint(100, 300)
        enemy_dfn = random.randint(100, 300)

        result = "WIN" if atk - enemy_dfn > enemy_atk - dfn else "LOSE"

        await q.edit_message_text(f"""
⚔️ جنگ

شما: {my_country}
دشمن: {enemy}
نوع مرز: {border_type}

ATK شما: {atk}
DEF شما: {dfn}

نتیجه: {result}
""", reply_markup=back())

# ================= MAIN =================

def main():

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))

    print("🚀 FINAL ICE WORLD RUNNING")

    app.run_polling()

if __name__ == "__main__":
    main()