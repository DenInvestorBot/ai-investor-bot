import os
import logging
import importlib
from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import Updater, CommandHandler

from screener_config import ScreenerConfig
from screener import run_screener
import rbne_monitor  # 👈 добавлен импорт RBNE

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ai-investor-bot")

def _get_env_any(names):
    for n in names:
        v = os.environ.get(n)
        if v:
            if n != "TELEGRAM_BOT_TOKEN":
                logger.info("Использую токен из ENV '%s'", n)
            return v
    return None

def _resolve_runner(module_name, preferred=("run", "main", "run_*", "monitor", "check")):
    try:
        m = importlib.import_module(module_name)
    except Exception as e:
        logger.exception("Не удалось импортировать модуль %s", module_name)
        def _stub():
            logger.error("%s: модуль не импортирован (%s)", module_name, e)
        return _stub
    for name in preferred:
        if "*" in name:
            continue
        fn = getattr(m, name, None)
        if callable(fn):
            return fn
    for name in dir(m):
        if name.startswith("run_") and callable(getattr(m, name)):
            return getattr(m, name)
    def _runner():
        logger.warning("%s: не найдено ожидаемых функций — пропускаю тик.", module_name)
    return _runner

# --- Telegram ---
def cmd_start(update, context):
    update.message.reply_text("🤖 AI-Investor-Bot активен! Используй /status.")

def cmd_status(update, context):
    update.message.reply_text("✅ Бот работает. Мониторы: crypto, ipo, reddit, screener, rbne.")

def main():
    token = _get_env_any(["TELEGRAM_BOT_TOKEN", "BOT_TOKEN", "TG_BOT_TOKEN"])
    if not token:
        raise ValueError("Отсутствует токен Telegram (проверь TELEGRAM_BOT_TOKEN / BOT_TOKEN / TG_BOT_TOKEN)")

    updater = Updater(token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CommandHandler("status", cmd_status))

    scheduler = BackgroundScheduler(timezone="Europe/Riga")

    ENABLE_CRYPTO   = os.getenv("ENABLE_CRYPTO", "1") not in ("0", "false", "False")
    ENABLE_IPO      = os.getenv("ENABLE_IPO", "1") not in ("0", "false", "False")
    ENABLE_REDDIT   = os.getenv("ENABLE_REDDIT", "1") not in ("0", "false", "False")
    ENABLE_SCREENER = os.getenv("ENABLE_SCREENER", "1") not in ("0", "false", "False")
    ENABLE_RBNE     = os.getenv("ENABLE_RBNE", "1") not in ("0", "false", "False")  # 👈 новая переменная

    if ENABLE_CRYPTO:
        run_crypto_monitor = _resolve_runner("crypto_monitor",
                                             preferred=("run_crypto_monitor", "run", "main", "collect_new_coins"))
        scheduler.add_job(run_crypto_monitor, "interval", hours=12, id="crypto_trending")

    if ENABLE_IPO:
        run_ipo_monitor = _resolve_runner("ipo_monitor", preferred=("run_ipo_monitor", "run", "main"))
        scheduler.add_job(run_ipo_monitor, "interval", hours=6, id="ipo_monitor")

    if ENABLE_REDDIT:
        run_reddit_monitor = _resolve_runner("reddit_monitor", preferred=("run_reddit_monitor", "run", "main"))
        scheduler.add_job(run_reddit_monitor, "interval", hours=1, id="reddit_monitor")

    if ENABLE_SCREENER:
        cfg = ScreenerConfig()
        scheduler.add_job(lambda: run_screener(cfg), "cron", minute="*/15", id="cheap_x_screener")

    if ENABLE_RBNE:
        scheduler.add_job(rbne_monitor.run_once, "interval", minutes=2, id="rbne_monitor")  # 👈 RBNE-монитор каждые 2 минуты

    scheduler.start()
    logger.info("Bot starting polling...")
    updater.start_polling(clean=True)
    updater.idle()

if __name__ == "__main__":
    main()
