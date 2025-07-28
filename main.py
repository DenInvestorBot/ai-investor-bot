from apscheduler.schedulers.blocking import BlockingScheduler
from ipo_monitor import run_ipo_monitor
from crypto_monitor import run_crypto_analysis

scheduler = BlockingScheduler()

@scheduler.scheduled_job('cron', hour=21, minute=0)
def scheduled_tasks():
    try:
        run_ipo_monitor()
    except Exception as e:
        print(f"❌ Ошибка в run_ipo_monitor: {e}")

    try:
        run_crypto_analysis()
    except Exception as e:
        print(f"❌ Ошибка в run_crypto_analysis: {e}")

if __name__ == "__main__":
    scheduler.start()
