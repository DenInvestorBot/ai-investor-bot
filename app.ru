import os
import sys
import time
import logging
import importlib
from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import Updater, CommandHandler

print("DEBUG: starting app.py (no direct crypto imports)", flush=True)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ai-investor-bot")

def _resolve_runner(module_name, preferred=("run_crypto_monitor","run","main","collect_new_coins","monitor","check")):
    try:
        m = importlib.import_module(module_name)
        print(f"DEBUG: imported {module_name} from {getattr(m, '__file__', '?')}", flush=True)
    except Exception as e:
        logger.exception("Не удалось импортировать модуль %s", module_name)
        def _stub():
            logger.error("%s: модуль не импортирован (%s)", module_name, e)
        return _stub
    for name in preferred:
        fn = getattr(m, name, None)
        if callable(fn):
            print(f"DEBUG: using {module_name}.{name}()", flush=True)
            return fn
    def _runner():
        logger.warning("%s: нет ожидаемых функций (%s) — пропускаю тик.", module_name, ", ".join(preferred))
    return _runner

def cmd_start(update, context):
    update.message.reply_text("🤖 AI-Investor-Bot активен! Используй /status.")

def cmd_status(update, context):
    update.message.reply_text("✅ Бот работает. Мониторы: crypto, ipo, reddit, screener.")

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Не найден TELEGRAM_BOT_TOKEN в переменных окружения")
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CommandHandler("status", cmd_status))

    scheduler = BackgroundScheduler(timezone="Europe/Riga")

    # Задачи
    run_crypto_monitor = _resolve_runner("crypto_monitor", preferred=("run_crypto_monitor","run","main","collect_new_coins"))
    scheduler.add_job(run_crypto_monitor, "interval", minutes=30, id="crypto_trending")

    run_ipo_monitor = _resolve_runner("ipo_monitor", preferred=("run_ipo_monitor","run","main"))
    scheduler.add_job(run_ipo_monitor, "interval", hours=6, id="ipo_monitor")

    run_reddit_monitor = _resolve_runner("reddit_monitor", preferred=("run_reddit_monitor","run","main"))
    scheduler.add_job(run_reddit_monitor, "interval", hours=1, id="reddit_monitor")

    # Скринер дешёвых x-охотников
    from screener_config import ScreenerConfig
    from screener import run_screener
    cfg = ScreenerConfig()
    scheduler.add_job(lambda: run_screener(cfg), "cron", minute="*/15", id="cheap_x_screener")

    scheduler.start()
    logger.info("Bot starting polling…")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
