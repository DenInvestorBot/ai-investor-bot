from apscheduler.schedulers.blocking import BlockingScheduler
import pytz
from ipo_monitor import run_ipo_monitor
from crypto_monitor import run_crypto_analysis

scheduler = BlockingScheduler(timezone=pytz.UTC)

@scheduler.scheduled_job('cron', hour=21, minute=0)
def scheduled_tasks():
    try:
        print("⏰ Запуск анализа IPO...")
        run_ipo_monitor()
    except Exception as e:
        print(f"❌ Ошибка в IPO: {e}")

    try:
        print("⏰ Запуск анализа крипты...")
        run_crypto_analysis()
    except Exception as e:
        print(f"❌ Ошибка в криптоанализе: {e}")

if __name__ == "__main__":
    print("✅ Планировщик стартовал (ежедневно в 21:00 UTC)")
    scheduler.start()
