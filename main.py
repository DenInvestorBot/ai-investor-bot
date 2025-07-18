import os
import logging
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from crypto_monitor import run_crypto_analysis
from ipo_monitor import run_ipo_monitor
from reddit_monitor import run_reddit_monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Telegram команда
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Я AI-инвестор бот. Ожидаю новостей о крипте и IPO!")

# Главная задача
def job():
    logger.info("⏱ Запуск фоновой задачи...")
    run_crypto_analysis()
    run_ipo_monitor()
    run_reddit_monitor()

def main():
    logger.info("🤖 AI-инвестор бот запущен!")

    # Слушаем Telegram
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))

    # Планировщик
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(job, 'interval', hours=6)
    scheduler.start()

    logger.info("🚀 Запуск мониторинга крипты, IPO и Reddit...")
    job()  # первый запуск сразу

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
