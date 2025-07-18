import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from datetime import datetime
import pytz
import os

from crypto_monitor import run_crypto_analysis
from ipo_monitor import run_ipo_monitor
from reddit_monitor import run_reddit_monitor

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def job():
    try:
        logger.info("🚀 Запуск мониторинга крипты, IPO и Reddit...")
        run_crypto_analysis()
        run_ipo_monitor()
        run_reddit_monitor()  # Пока заглушка, всё ок
    except Exception as e:
        logger.error(f"❌ Ошибка в job(): {e}")

def main():
    logger.info("🤖 AI-инвестор бот запущен!")

    scheduler = BlockingScheduler(
        timezone=pytz.utc,
        executors={'default': ThreadPoolExecutor(2)}
    )

    scheduler.add_job(job, 'interval', hours=6)
    job()  # Первый запуск сразу
    scheduler.start()

if __name__ == "__main__":
    main()
