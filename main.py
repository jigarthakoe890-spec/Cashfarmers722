import logging
import os
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from appwrite.client import Client
from appwrite.services.databases import Databases
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

databases = Databases(client)

# Appwrite માં યુઝર ઉમેરવો
def add_user_to_appwrite(user_id):
    try:
        str_user_id = str(user_id)
        result = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=COLLECTION_ID,
            queries=[Query.equal('user_id', str_user_id)]
        )
        if result['total'] == 0:
            databases.create_document(
                database_id=DATABASE_ID,
                collection_id=COLLECTION_ID,
                document_id='unique()',
                data={'user_id': str_user_id}
            )
            print(f"User {str_user_id} added successfully!")
    except Exception as e:
        print(f"Appwrite Add Error: {e}")

# Appwrite માંથી બધા યુઝર્સના ID મેળવવો
def get_all_users_from_appwrite():
    try:
        result = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=COLLECTION_ID
        )
        users = []
        for doc in result['documents']:
            if 'user_id' in doc and doc['user_id']:
                users.append(doc['user_id'])
        print(f"Total Users Found in Database: {len(users)}")
        return users
    except Exception as e:
        print(f"Appwrite Get Error: {e}")
        return []

# --- ૩. /start કમાન્ડ ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user_to_appwrite(user_id)
    await update.message.reply_text("હેલો! બોટમાં તમારું સ્વાગત છે.")

# --- ૪. મેસેજ અને ફોટો હેન્ડલર ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # નવા યુઝરને ડેટાબેઝમાં સાચવો
    add_user_to_appwrite(user_id)
    
    # ૧. જો તમે (Owner) કોઈ મેસેજ કે ફોટો મોકલો:
    if user_id == OWNER_ID:
        # જો તમે યુઝરના ફોરવર્ડ થયેલા મેસેજ પર Reply આપો છો:
        if update.message.reply_to_message and update.message.reply_to_message.forward_from:
            target_user_id = update.message.reply_to_message.forward_from.id
            await context.bot.copy_message(
                chat_id=target_user_id,
                from_chat_id=OWNER_ID,
                message_id=update.message.message_id
            )
        # જો તમે Reply આપ્યા વગર ડાયરેક્ટ મેસેજ/ફોટો મૂકો છો (બધાને જશે):
        else:
            users = get_all_users_from_appwrite()
            for uid in users:
                if str(uid) != str(OWNER_ID):
                    try:
                        await context.bot.copy_message(
                            chat_id=int(uid),
                            from_chat_id=OWNER_ID,
                            message_id=update.message.message_id
                        )
                    except Exception as e:
                        print(f"Error sending to {uid}: {e}")

    # ૨. જો સામાન્ય યુઝર ફોટો કે મેસેજ મોકલે:
    else:
        # યુઝરનો મેસેજ/ફોટો તમને સીધો ફોરવર્ડ થશે
        await context.bot.forward_message(
            chat_id=OWNER_ID,
            from_chat_id=user_id,
            message_id=update.message.message_id
        )

def main():
    t = Thread(target=run_flask)
    t.start()

    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    application.run_polling()

if __name__ == '__main__':
    main()