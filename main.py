import logging
from telegram import Bot
import os
from apscheduler.schedulers.blocking import BlockingScheduler

# Импортируем все функции мониторинга
from crypto_monitor import run_crypto_analysis
from ipo_monitor import main as run_ipo_monitor
from reddit_monitor import run_reddit_monitor

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=BOT_TOKEN)

def job():
    logger.info("🚀 Запуск мониторинга крипты, IPO и Reddit...")
    run_crypto_analysis()
    run_ipo_monitor()
    run_reddit_monitor()

def main():
    logger.info("🤖 AI-инвестор бот запущен!")
    scheduler = BlockingScheduler()
    # Запуск мониторинга сразу при старте
    job()
    # Планируем ежедневную сводку на 21:00
    scheduler.add_job(job, 'cron', hour=21, minute=0)
    scheduler.start()

if __name__ == '__main__':
    main()
