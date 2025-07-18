import logging
import os
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

from crypto_monitor import run_crypto_analysis
from ipo_monitor import run_ipo_monitor
from reddit_monitor import run_reddit_monitor

# Логгирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=BOT_TOKEN)

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привет! Я AI-инвестор бот. Жду сигналы рынка...")

def job():
    try:
        logger.info("🚀 Запуск мониторинга крипты, IPO и Reddit...")
        run_crypto_analysis()
        run_ipo_monitor()
        run_reddit_monitor()  # Пока может быть заглушка
    except Exception as e:
        logger.error(f"❌ Ошибка в job(): {e}")

def main():
    logger.info("🤖 AI-инвестор бот запущен!")

    # Обработка Telegram-команд
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))

    # Планировщик
    scheduler = BackgroundScheduler(timezone=utc)
    scheduler.add_job(job, 'interval', hours=6)
    scheduler.start()

    job()  # Первый запуск сразу
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
