from apscheduler.schedulers.blocking import BlockingScheduler
from ipo_monitor import run_ipo_monitor
from crypto_monitor import run_crypto_analysis

scheduler = BlockingScheduler()

# Запуск ежедневно в 21:00
@scheduler.scheduled_job('cron', hour=21, minute=0)
def daily_report():
    run_ipo_monitor()
    run_crypto_analysis()

if __name__ == "__main__":
    scheduler.start()
