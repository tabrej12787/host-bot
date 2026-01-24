import os
import time
import signal
import subprocess
import json
from threading import Lock, Thread
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

# ============ RENDER PORT SETUP ============
# Render ko zinda rehne ke liye ek web server chahiye hota hai
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot is Running"

def run_flask():
    # Render default port 10000 use karta hai
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)

# ============ CONFIG ============
BOT_TOKEN = "8424462856:AAGSOPieZ_wTs0VKxxO7Do4azscyajcYPtk"
ADMIN_IDS = [6073395870]
FREE_LIMIT = 2

BASE_DIR = "bots"
os.makedirs(BASE_DIR, exist_ok=True)

bots = {}
user_type = {}
lock = Lock()

# ============ KEYBOARDS ============
MAIN_KB = ReplyKeyboardMarkup(
    [["➕ Add Bot", "📋 My Bots"], ["⛔ Kill Bot"]],
    resize_keyboard=True
)

ADMIN_KB = ReplyKeyboardMarkup(
    [["📢 Global Broadcast"], ["⭐ Add Premium", "⬅ Back"]],
    resize_keyboard=True
)

# ============ HELPERS ============
def is_admin(uid):
    return uid in ADMIN_IDS

def get_limit(uid):
    return 999 if user_type.get(uid) == "premium" else FREE_LIMIT

def kill(pid):
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except:
        pass

# ============ HANDLERS ============
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_type.setdefault(uid, "free")
    msg = (f"🤖 BOT HOST\n\n👤 Type: {user_type[uid]}\n⚡ Limit: {get_limit(uid)} bots\n\n")
    if is_admin(uid): msg += "\n/admin = Admin panel"
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=MAIN_KB)

async def admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("👑 ADMIN PANEL", reply_markup=ADMIN_KB)

async def text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    t = update.message.text
    if t == "/admin": return await admin(update, ctx)
    
    if t == "➕ Add Bot":
        with lock:
            if len(bots.get(uid, {})) >= get_limit(uid):
                return await update.message.reply_text("❌ Free limit khatam.")
        ctx.user_data["step"] = "name"
        return await update.message.reply_text("Bot name bhejo")

    if ctx.user_data.get("step") == "name":
        ctx.user_data["name"] = t
        ctx.user_data["step"] = "upload"
        return await update.message.reply_text("📂 bot.py upload karo")

    if t == "📋 My Bots":
        b = bots.get(uid, {})
        if not b: return await update.message.reply_text("No bots")
        msg = "🤖 YOUR BOTS\n\n" + "\n".join(b.keys())
        return await update.message.reply_text(msg)

    if t == "⛔ Kill Bot":
        ctx.user_data["step"] = "kill"
        return await update.message.reply_text("Bot ID bhejo")

    if ctx.user_data.get("step") == "kill":
        bid = t.strip()
        with lock:
            inf = bots.get(uid, {}).get(bid)
            if inf:
                kill(inf["p"].pid)
                bots[uid].pop(bid)
                return await update.message.reply_text("Bot stopped")
        return await update.message.reply_text("Invalid ID")

async def file_h(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if ctx.user_data.get("step") != "upload": return
    f = await update.message.document.get_file()
    data = (await f.download_as_bytearray()).decode()
    bid = f"bot{int(time.time())}"
    folder = f"{BASE_DIR}/{uid}"
    os.makedirs(folder, exist_ok=True)
    path = f"{folder}/{bid}.py"
    with open(path, "w") as fp: fp.write(data)
    p = subprocess.Popen(["python", path], start_new_session=True)
    with lock: bots.setdefault(uid, {})[bid] = {"p": p, "path": path}
    ctx.user_data.clear()
    await update.message.reply_text("▶ Bot RUNNING 🚀")

# ============ MAIN ============
def main():
    # Flask ko background thread mein start karein
    Thread(target=run_flask, daemon=True).start()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.Document.ALL, file_h))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    
    print("HOST BOT ONLINE WITH FLASK")
    app.run_polling()

if __name__ == "__main__":
    main()
