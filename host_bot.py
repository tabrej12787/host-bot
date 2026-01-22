import os, time, signal, subprocess, json
from threading import Lock
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

# ============ CONFIG ============
BOT_TOKEN = "8424462856:AAFONSWQLCi7XjqxqWIcoGvA7nyQyH3Ypl4"
ADMIN_IDS = [6073395870]
FREE_LIMIT = 2

BASE_DIR = "bots"
os.makedirs(BASE_DIR, exist_ok=True)

bots = {}
user_type = {}
lock = Lock()

# ============ KEYBOARDS ============
MAIN_KB = ReplyKeyboardMarkup(
    [
        ["➕ Add Bot", "📋 My Bots"],
        ["⛔ Kill Bot"]
    ], resize_keyboard=True
)

ADMIN_KB = ReplyKeyboardMarkup(
    [
        ["📢 Global Broadcast"],
        ["⭐ Add Premium", "⬅ Back"]
    ], resize_keyboard=True
)

# ============ HELPERS ============
def is_admin(uid):
    return uid in ADMIN_IDS

def get_limit(uid):
    return 999 if user_type.get(uid)=="premium" else FREE_LIMIT

def kill(pid):
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except:
        pass

# ============ CODE INJECT ============
INJECT = """
# ==== AUTO TRACK ENABLED ====
import json
UFILE="users.json"

def _save(uid):
    try:
        try:
            u=json.load(open(UFILE))
        except:
            u=[]
        if uid not in u:
            u.append(uid)
            json.dump(u,open(UFILE,"w"))
    except: pass

async def _track(update,ctx):
    _save(update.effective_user.id)
"""

def inject(code):
    return INJECT + "\n" + code

# ============ START ============
async def start(update:Update,ctx):
    uid=update.effective_user.id
    user_type.setdefault(uid,"free")

    msg=(f"🤖 BOT HOST\n\n"
         f"👤 Type: {user_type[uid]}\n"
         f"⚡ Limit: {get_limit(uid)} bots\n\n"
         "⚠ NOTICE:\n"
         "Is system me *Global Broadcast* enabled hai.\n"
         "Admin kabhi bhi announcement bhej sakta hai.\n\n")

    if is_admin(uid):
        msg+="\n/admin = Admin panel"

    await update.message.reply_text(msg,parse_mode="Markdown",reply_markup=MAIN_KB)

# ============ ADMIN ============
async def admin(update,ctx):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text(
        "👑 ADMIN PANEL",
        reply_markup=ADMIN_KB
    )

# ============ TEXT ============
async def text(update:Update,ctx):
    uid=update.effective_user.id
    t=update.message.text

    # ---- ADMIN ----
    if t=="/admin":
        return await admin(update,ctx)

    if t=="📢 Global Broadcast" and is_admin(uid):
        ctx.user_data["step"]="bc"
        return await update.message.reply_text("Message bhejo")

    if t=="⭐ Add Premium" and is_admin(uid):
        ctx.user_data["step"]="prem"
        return await update.message.reply_text("User ID bhejo")

    if t=="⬅ Back" and is_admin(uid):
        return await start(update,ctx)

    # ---- USER ----
    if t=="➕ Add Bot":
        with lock:
            if len(bots.get(uid,{}))>=get_limit(uid):
                return await update.message.reply_text(
                    "❌ Free limit khatam.\nAdmin se premium lo."
                )
        ctx.user_data["step"]="name"
        return await update.message.reply_text("Bot name bhejo")

    if ctx.user_data.get("step")=="name":
        ctx.user_data["name"]=t
        ctx.user_data["step"]="upload"
        return await update.message.reply_text("📂 bot.py upload karo")

    if t=="📋 My Bots":
        with lock:
            b=bots.get(uid,{})
        if not b:
            return await update.message.reply_text("No bots")
        msg="🤖 YOUR BOTS\n\n"
        for i in b: msg+=f"{i}\n"
        return await update.message.reply_text(msg)

    if t=="⛔ Kill Bot":
        ctx.user_data["step"]="kill"
        return await update.message.reply_text("Bot ID bhejo")

    if ctx.user_data.get("step")=="kill":
        bid=t.strip()
        with lock:
            inf=bots.get(uid,{}).get(bid)
        if not inf:
            return await update.message.reply_text("Invalid ID")
        kill(inf["p"].pid)
        bots[uid].pop(bid)
        ctx.user_data.clear()
        return await update.message.reply_text("Bot stopped")

    # ---- ADMIN STEPS ----
    if ctx.user_data.get("step")=="bc" and is_admin(uid):
        msg=t
        for u in bots:
            try:
                await ctx.bot.send_message(u,msg)
            except: pass
        ctx.user_data.clear()
        return await update.message.reply_text("✅ Broadcast sent")

    if ctx.user_data.get("step")=="prem" and is_admin(uid):
        user_type[int(t)]="premium"
        ctx.user_data.clear()
        return await update.message.reply_text("⭐ Premium added")

# ============ FILE ============
async def file_h(update,ctx):
    uid=update.effective_user.id
    if ctx.user_data.get("step")!="upload": return

    f=await update.message.document.get_file()
    data=(await f.download_as_bytearray()).decode()

    code=inject(data)

    bid=f"bot{int(time.time())}"
    folder=f"{BASE_DIR}/{uid}"
    os.makedirs(folder,exist_ok=True)
    path=f"{folder}/{bid}.py"

    open(path,"w").write(code)

    p=subprocess.Popen(["python",path],start_new_session=True)

    with lock:
        bots.setdefault(uid,{})[bid]={
            "p":p,"path":path
        }

    ctx.user_data.clear()

    await update.message.reply_text(
        "⚠ NOTICE:\n"
        "Global Broadcast enabled.\n\n"
        "▶ Bot RUNNING 🚀"
    )

# ============ MAIN ============
def main():
    app=ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("admin",admin))
    app.add_handler(MessageHandler(filters.Document.ALL,file_h))
    app.add_handler(MessageHandler(filters.TEXT,text))

    print("HOST BOT ONLINE")
    app.run_polling()

if __name__=="__main__":
    main()