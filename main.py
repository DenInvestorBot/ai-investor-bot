import logging
from telegram.ext import Updater, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import os
from crypto_monitor import run_crypto_analysis
from ipo_monitor import run_ipo_monitor
from reddit_monitor import run_reddit_monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

updater = Updater(BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

def start(update, context):
    update.message.reply_text("Привет! Я AI-инвестор бот. Буду держать тебя в курсе новостей IPO, крипты и Reddit 🚀")

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

    dispatcher.add_handler(CommandHandler("start", start))
    updater.start_polling()

    # Сразу первый запуск job
    job()

    # Запуск job каждый день в 21:00 по МСК
    scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Moscow"))
    scheduler.add_job(job, CronTrigger(hour=21, minute=0))
    scheduler.start()

    updater.idle()

if __name__ == "__main__":
    main()
