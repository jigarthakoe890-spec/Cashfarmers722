import logging
import os
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.query import Query

# --- ૧. Render માટે Web Server સેટઅપ ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- ૨. ટેલિગ્રામ અને Appwrite સેટિંગ્સ ---
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

def add_user_to_appwrite(user_id):
    try:
        result = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=COLLECTION_ID,
            queries=[Query.equal('user_id', user_id)]
        )
        if result['total'] == 0:
            databases.create_document(
                database_id=DATABASE_ID,
                collection_id=COLLECTION_ID,
                document_id='unique()',
                data={'user_id': user_id}
            )
    except Exception as e:
        print(f"Appwrite Error (Add): {e}")

def get_all_users_from_appwrite():
    try:
        result = databases.list_documents(
            database_id=DATABASE_ID,
            collection_id=COLLECTION_ID
        )
        return [doc['user_id'] for doc in result['documents']]
    except Exception as e:
        print(f"Appwrite Error (Get): {e}")
        return []

# --- ૩. ટેલિગ્રામ હેન્ડલર ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user_to_appwrite(user_id)
    
    if user_id == OWNER_ID:
        if update.message.reply_to_message and update.message.reply_to_message.forward_from:
            target_user_id = update.message.reply_to_message.forward_from.id
            await context.bot.copy_message(
                chat_id=target_user_id,
                from_chat_id=OWNER_ID,
                message_id=update.message.message_id
            )
        else:
            users = get_all_users_from_appwrite()
            for uid in users:
                if uid != OWNER_ID:
                    try:
                        await context.bot.copy_message(
                            chat_id=uid,
                            from_chat_id=OWNER_ID,
                            message_id=update.message.message_id
                        )
                    except Exception:
                        pass
    else:
        await context.bot.forward_message(
            chat_id=OWNER_ID,
            from_chat_id=user_id,
            message_id=update.message.message_id
        )

def main():
    # પૃષ્ઠભૂમિમાં Web Server ચાલુ રાખવું
    t = Thread(target=run_flask)
    t.start()

    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()
