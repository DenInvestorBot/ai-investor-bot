from apscheduler.schedulers.blocking import BlockingScheduler
import pytz

from ipo_monitor import run_ipo_monitor
from crypto_monitor import run_crypto_analysis
from reddit_monitor import run_reddit_monitor
from status_check import run_status_check

# Запускаем по часовому поясу Риги — 21:00 Europe/Riga ежедневно
riga_tz = pytz.timezone("Europe/Riga")
scheduler = BlockingScheduler(timezone=riga_tz)

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

    try:
        print("⏰ Запуск мониторинга Reddit...")
        run_reddit_monitor()
    except Exception as e:
        print(f"❌ Ошибка в Reddit-мониторе: {e}")

if __name__ == "__main__":
    print("✅ Планировщик стартовал (ежедневно в 21:00 Europe/Riga)")
    scheduler.start()
