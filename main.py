import logging
import os
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from appwrite.client import Client
from appwrite.services.tables_db import TablesDB
from appwrite.query import Query

# --- ૧. Render માટે Web Server ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- ૨. કન્ફિગરેશન ---
TOKEN = '8857953077:AAFnPRz6smvpPILJHjhG5tyagd6C3YS2-ic'
OWNER_ID = 6079756619

APPWRITE_ENDPOINT = 'https://fra.cloud.appwrite.io/v1'
APPWRITE_PROJECT_ID = '6985aa6e0018fb6d3ef8'
DATABASE_ID = '6a0c59ac002413005872'
COLLECTION_ID = 'users' 
APPWRITE_API_KEY = 'Standard_8e05de023d2eeebe5292137816c5f400e6a1749ff3b4594b9e42cab0407ae31cacbe197bb1b262b481a78fcbe7bcf187b86e5d2e37a3e827fd045604f4d39e5722bb6d529a259c8a43b52e16f38699d2377d055fa96b3498aef572c3e65d85350411d5a5418644d0aca4d8fff769046e87ea9d5397c1793ce11bf28e215f4ba4'

client = Client()
client.set_endpoint(APPWRITE_ENDPOINT)
client.set_project(APPWRITE_PROJECT_ID)
client.set_key(APPWRITE_API_KEY)

tables_db = TablesDB(client)

# Appwrite માં યુઝર ઉમેરવો
def add_user_to_appwrite(user_id):
    try:
        u_id = int(user_id)
        result = tables_db.list_rows(
            database_id=DATABASE_ID,
            table_id=COLLECTION_ID,
            queries=[Query.equal('user_id', u_id)]
        )
        total = getattr(result, 'total', 0)
        if total == 0:
            tables_db.create_row(
                database_id=DATABASE_ID,
                table_id=COLLECTION_ID,
                row_id='unique()',
                data={'user_id': u_id}
            )
            print(f"User {u_id} added successfully!")
            return True, "Success"
        return True, "Already Exists"
    except Exception as e:
        err_msg = str(e)
        print(f"Appwrite Add Error: {err_msg}")
        return False, err_msg

# Appwrite માંથી બધા યુઝર્સના ID મેળવવા
def get_all_users_from_appwrite():
    try:
        result = tables_db.list_rows(
            database_id=DATABASE_ID,
            table_id=COLLECTION_ID
        )
        users = []
        rows = getattr(result, 'rows', [])
        for row in rows:
            u_id = getattr(row, 'user_id', None)
            if u_id is None and hasattr(row, 'data'):
                u_id = row.data.get('user_id')
            if u_id is None and isinstance(row, dict):
                u_id = row.get('user_id')
            if u_id is not None:
                users.append(int(u_id))
        return users, None
    except Exception as e:
        err_msg = str(e)
        print(f"Appwrite Get Error: {err_msg}")
        return [], err_msg

# --- ૩. /start કમાન્ડ ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    success, err = add_user_to_appwrite(user_id)
    
    if success:
        await update.message.reply_text("Welcome! 🌟 You are super important to us, and we're always here for you! ✨")
    else:
        await update.message.reply_text(f"⚠️ Appwrite Add Error:\n`{err}`", parse_mode="Markdown")

# --- ૪. મેસેજ અને બ્રોડકાસ્ટ હેન્ડલર ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # યુઝર ઉમેરો
    add_user_to_appwrite(user_id)
    
    # જો ઓનર (તમે) મેસેજ કે ફોટો મોકલો:
    if user_id == OWNER_ID:
        
        # CASE A: જો તમે યુઝરના ફોરવર્ડ મેસેજ પર Reply આપી રહ્યા છો
        if update.message.reply_to_message:
            reply_msg = update.message.reply_to_message
            target_user_id = None
            
            # Safe attribute check for new python-telegram-bot versions
            forward_from = getattr(reply_msg, 'forward_from', None)
            forward_origin = getattr(reply_msg, 'forward_origin', None)
            
            if forward_from:
                target_user_id = forward_from.id
            elif forward_origin and hasattr(forward_origin, 'sender_user'):
                target_user_id = forward_origin.sender_user.id
            
            if target_user_id:
                try:
                    await context.bot.copy_message(
                        chat_id=int(target_user_id),
                        from_chat_id=OWNER_ID,
                        message_id=update.message.message_id
                    )
                    await update.message.reply_text(f"✅ યુઝર ({target_user_id}) ને રિપ્લાય મોકલાઈ ગયો.")
                    return
                except Exception as e:
                    await update.message.reply_text(f"❌ Telegram Copy Error:\n`{e}`", parse_mode="Markdown")
                    return
            else:
                await update.message.reply_text("⚠️ આ યુઝરની Telegram Privacy ના લીધે ID મળી શક્યો નથી.")
                return

        # CASE B: ઓનરે ડાયરેક્ટ મેસેજ કર્યો (બધાને બ્રોડકાસ્ટ)
        users, appwrite_err = get_all_users_from_appwrite()
        
        if appwrite_err:
            await update.message.reply_text(f"🚨 Appwrite Fetch Error:\n`{appwrite_err}`", parse_mode="Markdown")
            return
            
        if not users:
            await update.message.reply_text("⚠️ Appwrite માં 0 યુઝર્સ મળ્યા! ડેટાબેઝ ખાલી છે.")
            return

        count = 0
        failed = 0
        error_details = []

        for uid in users:
            if int(uid) != OWNER_ID:
                try:
                    await context.bot.copy_message(
                        chat_id=int(uid),
                        from_chat_id=OWNER_ID,
                        message_id=update.message.message_id
                    )
                    count += 1
                except Exception as e:
                    failed += 1
                    error_details.append(f"ID {uid}: {str(e)}")

        msg = f"✅ સફળતાપૂર્વક મોકલાયા: *{count}*\n❌ નિષ્ફળ ગયા: *{failed}*"
        if error_details:
            msg += "\n\n*એરર વિગત:*\n" + "\n".join(error_details[:3])
            
        await update.message.reply_text(msg, parse_mode="Markdown")

    # જો સાદો યુઝર મેસેજ કરે (તો ઓનરને ફોરવર્ડ થશે):
    else:
        try:
            await context.bot.forward_message(
                chat_id=OWNER_ID,
                from_chat_id=user_id,
                message_id=update.message.message_id
            )
        except Exception as e:
            print(f"Forward error: {e}")

def main():
    t = Thread(target=run_flask)
    t.start()

    print("Bot is starting...")
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    application.run_polling()

if __name__ == '__main__':
    main()