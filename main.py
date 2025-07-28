import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from ipo_monitor import run_ipo_monitor
from crypto_monitor import run_crypto_analysis

# Часовой пояс (UTC можно заменить, например, на pytz.timezone("Europe/Riga"))
scheduler = BlockingScheduler(timezone=pytz.UTC)

@scheduler.scheduled_job('cron', hour=21, minute=0)
def scheduled_tasks():
    try:
        print("⏳ Запуск анализа IPO...")
        run_ipo_monitor()
    except Exception as e:
        print(f"❌ Ошибка в run_ipo_monitor: {e}")

    try:
        print("⏳ Запуск анализа криптовалют...")
        run_crypto_analysis()
    except Exception as e:
        print(f"❌ Ошибка в run_crypto_analysis: {e}")

if __name__ == "__main__":
    print("✅ Планировщик запущен (ежедневно в 21:00 UTC)")
    scheduler.start()
