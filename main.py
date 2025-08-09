import sys
import traceback
from apscheduler.schedulers.blocking import BlockingScheduler
import pytz

print("🚀 Инициализация бота...")

try:
    from ipo_monitor import run_ipo_monitor
    from crypto_monitor import run_crypto_analysis
    from reddit_monitor import run_reddit_monitor
    from status_check import run_status_check
except Exception as e:
    print("❌ Ошибка при импорте модулей:")
    traceback.print_exc()
    sys.exit(1)

# Настройка таймзоны
try:
    riga_tz = pytz.timezone("Europe/Riga")
except Exception as e:
    print(f"⚠️ Ошибка при установке таймзоны: {e}, используем UTC")
    riga_tz = pytz.UTC

scheduler = BlockingScheduler(timezone=riga_tz)

@scheduler.scheduled_job('cron', hour=21, minute=0)
def scheduled_tasks():
    print("🕒 Запуск ежедневных задач...")

    try:
        print("⏰ Запуск анализа IPO...")
        run_ipo_monitor()
        print("✅ IPO анализ завершён")
    except Exception as e:
        print("❌ Ошибка в IPO анализе:")
        traceback.print_exc()

    try:
        print("⏰ Запуск анализа криптовалют...")
        run_crypto_analysis()
        print("✅ Криптоанализ завершён")
    except Exception as e:
        print("❌ Ошибка в криптоанализе:")
        traceback.print_exc()

    try:
        print("⏰ Запуск мониторинга Reddit...")
        run_reddit_monitor()
        print("✅ Reddit мониторинг завершён")
    except Exception as e:
        print("❌ Ошибка в Reddit-мониторинге:")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        print("✅ Планировщик стартовал (ежедневно в 21:00 Europe/Riga)")
        scheduler.start()
    except Exception as e:
        print("❌ Ошибка при старте планировщика:")
        traceback.print_exc()
        sys.exit(1)
