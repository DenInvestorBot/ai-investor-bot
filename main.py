import os
import logging
import importlib
from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import Updater, CommandHandler

from screener_config import ScreenerConfig
from screener import run_screener

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ai-investor-bot")

# --- утилиты ---
def _get_env_any(names):
    for n in names:
        v = os.environ.get(n)
        if v:
            if n != "TELEGRAM_BOT_TOKEN":
                logger.info("Использую токен из ENV '%s'", n)
            return v
    return None

def _resolve_runner(module_name, preferred=("run_crypto_monitor","run","main","collect_new_coins","monitor","check")):
    try:
        m = importlib.import_module(module_name)
    except Exception as e:
        logger.exception("Не удалось импортировать модуль %s", module_name)
        def _stub():
            logger.error("%s: модуль не импортирован (%s)", module_name, e)
        return _stub
    for name in preferred:
        fn = getattr(m, name, None)
        if callable(fn):
            return fn
    def _runner():
        logger.warning("%s: не найдено ожидаемых функций (%s) — пропускаю тик.", module_name, ", ".join(preferred))
    return _runner

# --- команды TG ---
def cmd_start(update, context):
    update.message.reply_text("🤖 AI-Investor-Bot активен! Используй /status.")

def cmd_status(update, context):
    update.message.reply_text("✅ Бот работает. Мониторы: crypto, ipo, reddit, screener.")

# --- точка входа ---
def main():
    # Поддерживаем разные имена переменных
    token = _get_env_any(["TELEGRAM_BOT_TOKEN","BOT_TOKEN","TG_BOT_TOKEN"])
    if not token:
        logger.error("Не найден токен в ENV (искал: TELEGRAM_BOT_TOKEN, BOT_TOKEN, TG_BOT_TOKEN). "
                     "Проверь настройки Render → Environment.")
        raise ValueError("Отсутствует токен Telegram")

    updater = Updater(token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CommandHandler("status", cmd_status))

    scheduler = BackgroundScheduler(timezone="Europe/Riga")

    run_crypto_monitor = _resolve_runner("crypto_monitor",
                                         preferred=("run_crypto_monitor","run","main","collect_new_coins"))
    scheduler.add_job(run_crypto_monitor, "interval", minutes=30, id="crypto_trending")

    run_ipo_monitor = _resolve_runner("ipo_monitor", preferred=("run_ipo_monitor","run","main"))
    scheduler.add_job(run_ipo_monitor, "interval", hours=6, id="ipo_monitor")

    run_reddit_monitor = _resolve_runner("reddit_monitor", preferred=("run_reddit_monitor","run","main"))
    scheduler.add_job(run_reddit_monitor, "interval", hours=1, id="reddit_monitor")

    cfg = ScreenerConfig()
    scheduler.add_job(lambda: run_screener(cfg), "cron", minute="*/15", id="cheap_x_screener")

    scheduler.start()
    logger.info("Bot starting polling…")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
