import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from crypto_monitor import run_crypto_analysis
from ipo_monitor import run_ipo_monitor
from reddit_monitor import run_reddit_monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def job():
    logger.info("🚀 Запуск мониторинга крипты, IPO и Reddit...")
    
    try:
        run_crypto_analysis()
    except Exception as e:
        logger.error(f"❌ Ошибка в run_crypto_analysis: {e}")
    
    try:
        run_ipo_monitor()
    except Exception as e:
        logger.error(f"❌ Ошибка в run_ipo_monitor: {e}")
    
    try:
        run_reddit_monitor()
    except Exception as e:
        logger.error(f"❌ Ошибка в run_reddit_monitor: {e}")

def main():
    logger.info("🤖 AI-инвестор бот запущен!")

    scheduler = BlockingScheduler(timezone="UTC")  # используем pytz-совместимую зону
    scheduler.add_job(job, 'interval', hours=6)
    
    job()  # Первый запуск сразу
    scheduler.start()

if __name__ == "__main__":
    main()
