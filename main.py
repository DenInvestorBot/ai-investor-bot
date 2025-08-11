import os
import logging
import time
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from scheduler.advisor_scheduler import register_advisor_jobs

# ===== Исправленные импорты =====
from bot.advisor_jobs import run_tsla_gme_daily_job
from crypto_monitor import run_crypto_monitor
from ipo_monitor import run_ipo_monitor
from reddit_monitor import run_reddit_monitor
from status_check import run_status_check
from telegram import Bot

print("📄 [main] Запуск бота...")

# ===== Настройка переменных окружения =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID", "0"))

if not TELEGRAM_TOKEN or CHAT_ID == 0:
    print("❌ [main] TELEGRAM_TOKEN и/или CHAT_ID не заданы — бот не сможет отправлять сообщения")
else:
    print(f"✅ [main] TELEGRAM_TOKEN найден (начало: {TELEGRAM_TOKEN[:8]}...)")

# ===== Логирование =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ===== Инициализация Telegram-бота =====
bot = None
if TELEGRAM_TOKEN and CHAT_ID:
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        log.info("🚀 Telegram-бот инициализирован")
    except Exception as e:
        log.error(f"❌ Ошибка инициализации Telegram-бота: {e}")

# ===== Запуск планировщика =====
scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Riga"))

# ===== Запуск всех задач один раз при старте =====
try:
    run_crypto_monitor()
except Exception as e:
    log.error(f"[main] Ошибка при запуске run_crypto_monitor: {e}")

try:
    run_ipo_monitor()
except Exception as e:
    log.error(f"[main] Ошибка при запуске run_ipo_monitor: {e}")

try:
    run_reddit_monitor()
except Exception as e:
    log.error(f"[main] Ошибка при запуске run_reddit_monitor: {e}")

try:
    run_status_check()
except Exception as e:
    log.error(f"[main] Ошибка при запуске run_status_check: {e}")

# ===== Регистрируем задачу советника =====
try:
    register_advisor_jobs(scheduler)
except Exception as e:
    log.error(f"[main] Ошибка при регистрации advisor_jobs: {e}")

log.info("✅ Планировщик готов (ежедневно в 21:00 Europe/Riga)")

try:
    scheduler.start()
    log.info("🕒 Планировщик запущен")
except Exception as e:
    log.error(f"[main] Ошибка запуска планировщика: {e}")

# ===== Поддержка работы приложения =====
try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    log.info("⏹ Остановка бота по Ctrl+C")
    scheduler.shutdown()
