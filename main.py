import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from crypto_monitor import run_crypto_analysis
from ipo_monitor import run_ipo_monitor
from reddit_monitor import run_reddit_monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def job():
    logger.info("🚀 Запуск мониторинга крипты, IPO и Reddit...")
    run_crypto_analysis()
    run_ipo_monitor()
    run_reddit_monitor()

def main():
    logger.info("🤖 AI-инвестор бот запущен!")
    scheduler = BlockingScheduler()
    scheduler.add_job(job, 'interval', hours=6)
    scheduler.start()

if __name__ == "__main__":
    main()