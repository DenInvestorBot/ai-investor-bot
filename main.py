import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import Updater, CommandHandler

# Импорты твоих модулей
from crypto_monitor import run_crypto_monitor
from ipo_monitor import run_ipo_monitor
from reddit_monitor import run_reddit_monitor
from screener_config import ScreenerConfig
from screener import run_screener

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def start(update, context):
    update.message.reply_text("🤖 AI-Investor-Bot активен! Используй /status для проверки.")


def status(update, context):
    update.message.reply_text("✅ Бот работает и мониторит рынки.")


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Не найден TELEGRAM_BOT_TOKEN в переменных окружения")

    updater = Updater(token, use_context=True)
    dp = updater.dispatcher

    # Команды
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("status", status))

    # Планировщик
    scheduler = BackgroundScheduler(timezone="Europe/Riga")

    # 1) Crypto monitor (новые криптовалюты)
    scheduler.add_job(run_crypto_monitor, "interval", minutes=30)

    # 2) IPO monitor (новые IPO)
    scheduler.add_job(run_ipo_monitor, "interval", hours=6)

    # 3) Reddit monitor (анализ трендов)
    scheduler.add_job(run_reddit_monitor, "interval", hours=1)

    # 4) Screener дешёвых x-охотников (каждые 15 минут)
    cfg = ScreenerConfig()
    scheduler.add_job(lambda: run_screener(cfg), "cron", minute="*/15")

    scheduler.start()

    # Запуск Telegram-бота
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
