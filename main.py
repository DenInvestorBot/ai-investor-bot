import logging
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from crypto_monitor import run_crypto_analysis
from ipo_monitor import run_ipo_monitor
# from reddit_monitor import run_reddit_monitor  # Добавим позже

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def job():
    logger.info("🚀 Запуск мониторинга крипты, IPO и Reddit...")
    run_crypto_analysis()
    run_ipo_monitor()
    # run_reddit_monitor()  # Подключим позже

def main():
    logger.info("🤖 AI-инвестор бот запущен!")
    scheduler = BlockingScheduler(timezone=pytz.utc)  # или pytz.timezone("Europe/Riga")
    scheduler.add_job(job, 'interval', hours=6)
    job()  # Первый запуск сразу
    scheduler.start()

if __name__ == "__main__":
    main()
