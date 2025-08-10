import os
import logging
from scheduler.advisor_scheduler import register_advisor_jobs
from bot.advisor_jobs import run_tsla_gme_daily_job
from crypto_monitor import run_crypto_monitor
from ipo_monitor import run_ipo_monitor
from reddit_monitor import run_reddit_monitor
from status_check import run_status_check
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

# ===== Проверка токена =====
token = os.getenv("TELEGRAM_TOKEN")
print("DEBUG TOKEN START:", repr(token[:10] if token else "NO TOKEN"))

if not token:
    raise ValueError("❌ TELEGRAM_TOKEN не найден в переменных окружения Render!")

# ===== Логирование =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

log = logging.getLogger(__name__)

# ===== Инициализация бота =====
from telegram import Bot
bot = Bot(token=token)

log.info("🚀 Инициализация бота...")

# ===== Запуск планировщика =====
scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Riga"))

# Регистрируем существующие задачи
run_crypto_monitor()
run_ipo_monitor()
run_reddit_monitor()
run_status_check()
register_advisor_jobs(scheduler)

log.info("✅ Планировщик стартовал (ежедневно в 21:00 Europe/Riga)")

scheduler.start()

# Чтобы бот не завершался
import time
while True:
    time.sleep(60)
