import logging
import sqlite3
import asyncio
import html
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, ChatMemberHandler
from telegram.constants import ParseMode

# --- Configuration ---
TELEGRAM_TOKEN = "8570379697:AAEh1z9btIGVlqAWqJyZH8c2p_dKzRTHBkI"

# Database Setup
db = sqlite3.connect("bot_management.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS keywords (keyword TEXT PRIMARY KEY, response TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS group_settings (id TEXT PRIMARY KEY, val TEXT)")
db.commit()

async def is_admin(update: Update):
    if update.effective_chat.type == "private": return True
    member = await update.effective_chat.get_member(update.effective_user.id)
    return member.status in ['creator', 'administrator']

async def delete_messages(messages, delay=5):
    await asyncio.sleep(delay)
    for msg in messages:
        try:
            await msg.delete()
        except:
            pass

# --- Start Command (Tutorial) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        tutorial = (
            "🤖 **မြတ်နိုး Bot အသုံးပြုနည်း Tutorial**\n\n"
            "၁။ **Keyword ထည့်ရန်**\n"
            "   👉 /add hi / မင်္ဂလာပါ \n\n"
            "၂။ **ကြိုဆိုစာ/နှုတ်ဆက်စာ**\n"
            "   👉 /setwelcome / စာသား \n"
            "   👉 /setgoodbye / စာသား \n\n"
            "၃။ **Link ပိတ်/ဖွင့် ရန်**\n"
            "   👉 /setlink on (Link ပို့လျှင် ဖျက်မည်)\n"
            "   👉 /setlink off (Link ပို့တာ ခွင့်ပြုမည်)\n\n"
            "၄။ **Forward ပိတ်/ဖွင့် ရန်**\n"
            "   👉 /setforward on (Forward ပို့လျှင် ဖျက်မည်)\n"
            "   👉 /setforward off (Forward ပို့တာ ခွင့်ပြုမည်)\n\n"
            "⚠️ Group ထဲတွင် Admin ပေးထားရန် လိုအပ်ပါသည်။"
        )
        await update.message.reply_text(tutorial, parse_mode=ParseMode.MARKDOWN)
    else:
        try: await update.message.delete()
        except: pass

# --- Welcome Function ---
async def greet_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.chat_member.new_chat_member.status == "member":
        user = update.chat_member.new_chat_member.user
        if user.is_bot: return
        
        cursor.execute("SELECT val FROM group_settings WHERE id='welcome'")
        row = cursor.fetchone()
        welcome_custom_text = row[0] if row else "ကြိုဆိုပါတယ်"
        mention = f'<a href="tg://user?id={user.id}">{html.escape(user.first_name)}</a>'
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"{welcome_custom_text} {mention}",
            parse_mode=ParseMode.HTML
        )

# --- Admin Commands ---
async def set_link_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    status = context.args[0].lower() if context.args else ""
    if status in ['on', 'off']:
        cursor.execute("INSERT OR REPLACE INTO group_settings VALUES (?, ?)", ("link_protection", status))
        db.commit()
        m = await update.message.reply_text(f"✅ Link Protection ကို {status.upper()} လိုက်ပါပြီ။")
        asyncio.create_task(delete_messages([update.message, m]))

async def set_forward_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    status = context.args[0].lower() if context.args else ""
    if status in ['on', 'off']:
        cursor.execute("INSERT OR REPLACE INTO group_settings VALUES (?, ?)", ("forward_protection", status))
        db.commit()
        m = await update.message.reply_text(f"✅ Forward Protection ကို {status.upper()} လိုက်ပါပြီ။")
        asyncio.create_task(delete_messages([update.message, m]))

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    try:
        parts = update.message.text.split("/")
        if len(parts) >= 2:
            text = parts[-1].strip()
            cursor.execute("INSERT OR REPLACE INTO group_settings VALUES (?, ?)", ("welcome", text))
            db.commit()
            m = await update.message.reply_text(f"✅ ကြိုဆိုစာကို '{text}' လို့ မှတ်လိုက်ပါပြီ။")
            asyncio.create_task(delete_messages([update.message, m]))
    except: pass

async def set_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    try:
        parts = update.message.text.split("/")
        if len(parts) >= 2:
            text = parts[-1].strip()
            cursor.execute("INSERT OR REPLACE INTO group_settings VALUES (?, ?)", ("goodbye", text))
            db.commit()
            m = await update.message.reply_text(f"✅ နှုတ်ဆက်စာကို '{text}' လို့ မှတ်လိုက်ပါပြီ။")
            asyncio.create_task(delete_messages([update.message, m]))
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
            m = await update.message.reply_text(f"✅ '{key}' အတွက် အဖြေကို မှတ်လိုက်ပါပြီ။")
            asyncio.create_task(delete_messages([update.message, m]))
    except: pass

# --- General Handler ---
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg: return

    if msg.left_chat_member:
        cursor.execute("SELECT val FROM group_settings WHERE id='goodbye'")
        row = cursor.fetchone()
        goodbye_custom_text = row[0] if row else "တာတာ့နော်"
        mention = f'<a href="tg://user?id={msg.left_chat_member.id}">{html.escape(msg.left_chat_member.first_name)}</a>'
        await msg.reply_text(f"{goodbye_custom_text} {mention}", parse_mode=ParseMode.HTML)
        return

    if not await is_admin(update):
        # Link Protection
        cursor.execute("SELECT val FROM group_settings WHERE id='link_protection'")
        link_row = cursor.fetchone()
        link_status = link_row[0] if link_row else "on"
        if link_status == "on" and msg.entities and any(e.type in ['url', 'text_link'] for e in msg.entities):
            user_mention = f'<a href="tg://user?id={msg.from_user.id}">{html.escape(msg.from_user.first_name)}</a>'
            await msg.delete()
            await context.bot.send_message(chat_id=msg.chat_id, text=f"{user_mention} Link ပို့တာ မြတ်နိုးမကြိုက်ဘူးနော်!", parse_mode=ParseMode.HTML)
            return

        # Forward Protection
        cursor.execute("SELECT val FROM group_settings WHERE id='forward_protection'")
        fwd_row = cursor.fetchone()
        fwd_status = fwd_row[0] if fwd_row else "on"
        if fwd_status == "on" and msg.forward_origin:
            user_mention = f'<a href="tg://user?id={msg.from_user.id}">{html.escape(msg.from_user.first_name)}</a>'
            await msg.delete()
            await context.bot.send_message(chat_id=msg.chat_id, text=f"{user_mention} Forward စာတွေ မပို့ပါနဲ့ရှင်!", parse_mode=ParseMode.HTML)
            return

    if msg.text:
        cursor.execute("SELECT response FROM keywords WHERE keyword=?", (msg.text.lower().strip(),))
        row = cursor.fetchone()
        if row: await msg.reply_text(row[0])

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatMemberHandler(greet_chat_members, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("add", add_keyword))
    app.add_handler(CommandHandler("setwelcome", set_welcome))
    app.add_handler(CommandHandler("setgoodbye", set_goodbye))
    app.add_handler(CommandHandler("setlink", set_link_protection))
    app.add_handler(CommandHandler("setforward", set_forward_protection))
    app.add_handler(MessageHandler(filters.ALL, handle_messages))
    print("မြတ်နိုး Bot အလုပ်လုပ်နေပါပြီ...")
    app.run_polling(allowed_updates=["message", "chat_member"])

if __name__ == '__main__':
    main()
