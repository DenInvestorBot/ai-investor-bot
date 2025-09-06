import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import Updater, CommandHandler

# ---- Импорты наших задач
from crypto_monitor import run_crypto_monitor
from screener_config import ScreenerConfig
from screener import run_screener

# Заглушки (безопасные) — можно удалить, если у тебя есть боевые версии
try:
    from ipo_monitor import run_ipo_monitor
except Exception:  # noqa
    def run_ipo_monitor():
        logging.getLogger(__name__).info("IPO monitor: заглушка — задача пропущена")

try:
    from reddit_monitor import run_reddit_monitor
except Exception:  # noqa
    def run_reddit_monitor():
        logging.getLogger(__name__).info("Reddit monitor: заглушка — задача пропущена")


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ai-investor-bot")


def cmd_start(update, context):
    update.message.reply_text("🤖 AI-Investor-Bot активен! Используй /status.")


def cmd_status(update, context):
    update.message.reply_text("✅ Бот работает. Мониторы запущены: crypto, ipo, reddit, screener.")


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Не найден TELEGRAM_BOT_TOKEN в переменных окружения")

    # Telegram bot poller
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CommandHandler("status", cmd_status))

    # Планировщик задач
    scheduler = BackgroundScheduler(timezone="Europe/Riga")

    # 1) Трендовые монеты CoinGecko (краткая сводка)
    scheduler.add_job(run_crypto_monitor, "interval", minutes=30, id="crypto_trending")

    # 2) IPO мониторинг (заглушка, можно заменить своим модулем)
    scheduler.add_job(run_ipo_monitor, "interval", hours=6, id="ipo_monitor")

    # 3) Reddit мониторинг (заглушка, можно заменить своим модулем)
    scheduler.add_job(run_reddit_monitor, "interval", hours=1, id="reddit_monitor")

    # 4) Скринер «дешёвых x-охотников»
    cfg = ScreenerConfig()
    scheduler.add_job(lambda: run_screener(cfg), "cron", minute="*/15", id="cheap_x_screener")

    scheduler.start()

    logger.info("Bot starting polling…")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
