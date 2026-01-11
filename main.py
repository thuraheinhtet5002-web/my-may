import logging
import sqlite3
import asyncio
import html
import os  # ဒါကို အသစ်ထည့်ထားပါတယ်
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, ChatMemberHandler
from telegram.constants import ParseMode

# --- Configuration ---
# Render မှာ Token ကို လုံခြုံအောင် သိမ်းဖို့ os.getenv သုံးထားပါတယ်
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8570379697:AAEh1z9btIGVlqAWqJyZH8c2p_dKzRTHBkI")

# Database Setup
db = sqlite3.connect("bot_management.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS keywords (keyword TEXT PRIMARY KEY, response TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS group_settings (id TEXT PRIMARY KEY, val TEXT)")
db.commit()

# --- Functions (အရှေ့ကအတိုင်းပဲ ထားပါ) ---
async def is_admin(update: Update):
    if update.effective_chat.type == "private": return True
    member = await update.effective_chat.get_member(update.effective_user.id)
    return member.status in ['creator', 'administrator']

async def delete_messages(messages, delay=5):
    await asyncio.sleep(delay)
    for msg in messages:
        try: await msg.delete()
        except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        tutorial = (
            "🤖 **မြတ်နိုး Bot အသုံးပြုနည်း Tutorial**\n\n"
            "၁။ **Keyword ထည့်ရန်**\n"
            "   👉 /add hi / မင်္ဂလာပါ \n\n"
            "၂။ **ကြိုဆိုစာ/နှုတ်ဆက်စာ**\n"
            "   👉 /setwelcome / စာသား \n"
            "   👉 /setgoodbye / စာသား \n"
            "၃။ **Link ပိတ်/ဖွင့် ရန်**\n"
            "   👉 /setlink on \n"
            "⚠️ Group ထဲတွင် Admin ပေးထားရန် လိုအပ်ပါသည်။"
        )
        await update.message.reply_text(tutorial, parse_mode=ParseMode.MARKDOWN)

async def greet_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.chat_member.new_chat_member.status == "member":
        user = update.chat_member.new_chat_member.user
        cursor.execute("SELECT val FROM group_settings WHERE id='welcome'")
        row = cursor.fetchone()
        welcome_custom_text = row[0] if row else "ကြိုဆိုပါတယ်"
        mention = f'<a href="tg://user?id={user.id}">{html.escape(user.first_name)}</a>'
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{welcome_custom_text} {mention}", parse_mode=ParseMode.HTML)

async def set_link_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    status = context.args[0].lower() if context.args else ""
    if status in ['on', 'off']:
        cursor.execute("INSERT OR REPLACE INTO group_settings VALUES (?, ?)", ("link_protection", status))
        db.commit()
        await update.message.reply_text(f"✅ Link Protection {status.upper()}")

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    try:
        parts = update.message.text.split("/")
        if len(parts) >= 2:
            text = parts[-1].strip()
            cursor.execute("INSERT OR REPLACE INTO group_settings VALUES (?, ?)", ("welcome", text))
            db.commit()
            await update.message.reply_text(f"✅ ကြိုဆိုစာကို '{text}' လို့ မှတ်လိုက်ပါပြီ။")
    except: pass

async def add_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    try:
        raw_text = update.message.text.replace("/add", "", 1).strip()
        parts = raw_text.split("/", 1)
        if len(parts) >= 2:
            key, resp = parts[0].strip().lower(), parts[1].strip()
            cursor.execute("INSERT OR REPLACE INTO keywords VALUES (?, ?)", (key, resp))
            db.commit()
            await update.message.reply_text(f"✅ '{key}' အတွက် အဖြေကို မှတ်လိုက်ပါပြီ။")
    except: pass

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg: return
    if msg.text:
        cursor.execute("SELECT response FROM keywords WHERE keyword=?", (msg.text.lower().strip(),))
        row = cursor.fetchone()
        if row: await msg.reply_text(row[0])

# --- Main Function (Render အတွက် ပြင်ဆင်ထားသောအပိုင်း) ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatMemberHandler(greet_chat_members, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("add", add_keyword))
    app.add_handler(CommandHandler("setwelcome", set_welcome))
    app.add_handler(CommandHandler("setlink", set_link_protection))
    app.add_handler(MessageHandler(filters.ALL, handle_messages))

    # Render အတွက် Port setting (ဒါက Web Service အဖြစ် run ရင် လိုအပ်ပါတယ်)
    port = int(os.environ.get("PORT", 8080))
    
    print("မြတ်နိုး Bot အလုပ်လုပ်နေပါပြီ...")
    
    # Render မှာ polling နဲ့ပဲ run လို့ရပါတယ် (Web service ဖြစ်လို့ Port ပွင့်နေဖို့ပဲလိုတာပါ)
    app.run_polling(allowed_updates=["message", "chat_member"])

if name == '__main__':
    main()
