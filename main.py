import logging
from telegram import Bot, Update
from telegram.ext import CommandHandler, Updater, CallbackContext
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Я инвест-бот на Render!")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()