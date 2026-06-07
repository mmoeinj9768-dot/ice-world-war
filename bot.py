import sqlite3
import time
import threading
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8843735484:AAE_aljnuOE18YdcYfv8Qxaej-jj4SSBKGk"
CREATOR_ID = JENERAL_41

# ================= DB =================
db = sqlite3.connect("jeneral.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS warns(
    user_id INTEGER,
    group_id INTEGER,
    count INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS settings(
    group_id INTEGER PRIMARY KEY,
    warn_limit INTEGER DEFAULT 3,
    mute_time INTEGER DEFAULT 3600
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS timers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER,
    run_at INTEGER,
    repeat INTEGER,
    interval INTEGER,
    notify INTEGER,
    command TEXT
)
""")

db.commit()

# ================= HELPERS =================

def is_link(text):
    return text and ("http" in text or "t.me" in text)

def get_warn_limit(group_id):
    cur.execute("SELECT warn_limit, mute_time FROM settings WHERE group_id=?", (group_id,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO settings(group_id) VALUES (?)", (group_id,))
        db.commit()
        return 3, 3600
    return row

def add_warn(user_id, group_id):
    cur.execute("SELECT count FROM warns WHERE user_id=? AND group_id=?", (user_id, group_id))
    row = cur.fetchone()

    if row:
        count = row[0] + 1
        cur.execute("UPDATE warns SET count=? WHERE user_id=? AND group_id=?",
                    (count, user_id, group_id))
    else:
        count = 1
        cur.execute("INSERT INTO warns VALUES (?, ?, ?)", (user_id, group_id, 1))

    db.commit()
    return count

# ================= MESSAGE =================

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text or ""
    user_id = msg.from_user.id
    group_id = msg.chat.id

    if is_link(text):

        if user_id == CREATOR_ID:
            return

        limit, mute_time = get_warn_limit(group_id)

        warns = add_warn(user_id, group_id)

        await msg.delete()

        await msg.reply_text(f"🚫 لینک ممنوع\n⚠️ اخطار: {warns}/{limit}")

        if warns >= limit:
            await context.bot.restrict_chat_member(
                group_id,
                user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=int(time.time() + mute_time)
            )

# ================= TIMER ENGINE =================

def timer_engine(app):
    while True:
        now = int(time.time())

        cur.execute("SELECT * FROM timers WHERE run_at<=?", (now,))
        rows = cur.fetchall()

        for tid, gid, run_at, repeat, interval, notify, cmd in rows:

            if notify:
                try:
                    app.bot.send_message(gid, f"⏱ {cmd}")
                except:
                    pass

            if repeat == -1 or repeat > 1:
                new_repeat = -1 if repeat == -1 else repeat - 1
                cur.execute("""
                    UPDATE timers SET run_at=?, repeat=? WHERE id=?
                """, (now + interval, new_repeat, tid))
            else:
                cur.execute("DELETE FROM timers WHERE id=?", (tid,))

        db.commit()
        time.sleep(5)

# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 JENERAL ROBOT V3 ACTIVE")

async def setwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != CREATOR_ID:
        return

    gid = update.effective_chat.id
    limit = int(context.args[0])

    cur.execute("""
        INSERT INTO settings(group_id, warn_limit)
        VALUES(?, ?)
        ON CONFLICT(group_id) DO UPDATE SET warn_limit=excluded.warn_limit
    """, (gid, limit))

    db.commit()
    await update.message.reply_text("✅ تنظیم شد")

async def timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gid = update.effective_chat.id

    try:
        minutes = int(context.args[0])
        command = " ".join(context.args[1:])

        run_at = int(time.time()) + minutes * 60

        cur.execute("""
            INSERT INTO timers(group_id, run_at, repeat, interval, notify, command)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (gid, run_at, 1, minutes * 60, 1, command))

        db.commit()
        await update.message.reply_text("⏱ تایمر ثبت شد")

    except:
        await update.message.reply_text("❌ فرمت اشتباه")

# ================= RUN =================

def run_timer(app):
    t = threading.Thread(target=timer_engine, args=(app,))
    t.daemon = True
    t.start()

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setwarn", setwarn))
    app.add_handler(CommandHandler("timer", timer))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

    run_timer(app)

    print("BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main() 