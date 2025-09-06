import os
import time
import logging
import importlib
from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import Updater, CommandHandler
from telegram.error import Conflict

from screener_config import ScreenerConfig
from screener import run_screener

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
    """Импортирует модуль и возвращает подходящую функцию-раннер, иначе — заглушку."""
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


# --- Telegram команды ---
def cmd_start(update, context):
    update.message.reply_text("🤖 AI-Investor-Bot активен! Используй /status.")

def cmd_status(update, context):
    update.message.reply_text("✅ Бот работает. Мониторы: crypto, ipo, reddit, screener.")

def cmd_runall(update, context):
    try:
        msgs = []
        _resolve_runner("crypto_monitor", ("run_crypto_monitor","run","main","collect_new_coins"))()
        msgs.append("✓ crypto_monitor")
        _resolve_runner("ipo_monitor", ("run_ipo_monitor","run","main"))()
        msgs.append("✓ ipo_monitor")
        _resolve_runner("reddit_monitor", ("run_reddit_monitor","run","main"))()
        msgs.append("✓ reddit_monitor")
        cfg = ScreenerConfig(); run_screener(cfg)
        msgs.append("✓ screener")
        update.message.reply_text("Запустил:\n" + "\n".join(msgs))
    except Exception as e:
        logging.exception("runall error")
        update.message.reply_text(f"Ошибка runall: {e}")


def _setup_scheduler():
    scheduler = BackgroundScheduler(timezone="Europe/Riga")

    ENABLE_CRYPTO   = os.getenv("ENABLE_CRYPTO", "1") not in ("0","false","False")
    ENABLE_IPO      = os.getenv("ENABLE_IPO", "1") not in ("0","false","False")
    ENABLE_REDDIT   = os.getenv("ENABLE_REDDIT", "1") not in ("0","false","False")
    ENABLE_SCREENER = os.getenv("ENABLE_SCREENER", "1") not in ("0","false","False")

    if ENABLE_CRYPTO:
        run_crypto_monitor = _resolve_runner("crypto_monitor", ("run_crypto_monitor","run","main","collect_new_coins"))
        scheduler.add_job(run_crypto_monitor, "interval", minutes=30, id="crypto_trending")
    else:
        logger.info("Crypto monitor disabled via ENV")

    if ENABLE_IPO:
        run_ipo_monitor = _resolve_runner("ipo_monitor", ("run_ipo_monitor","run","main"))
        scheduler.add_job(run_ipo_monitor, "interval", hours=6, id="ipo_monitor")
    else:
        logger.info("IPO monitor disabled via ENV")

    if ENABLE_REDDIT:
        run_reddit_monitor = _resolve_runner("reddit_monitor", ("run_reddit_monitor","run","main"))
        scheduler.add_job(run_reddit_monitor, "interval", hours=1, id="reddit_monitor")
    else:
        logger.info("Reddit monitor disabled via ENV")

    if ENABLE_SCREENER:
        cfg = ScreenerConfig()
        scheduler.add_job(lambda: run_screener(cfg), "cron", minute="*/15", id="cheap_x_screener")
    else:
        logger.info("Screener disabled via ENV")

    scheduler.start()
    return scheduler


def main():
    token = _get_env_any(["TELEGRAM_BOT_TOKEN","BOT_TOKEN","TG_BOT_TOKEN"])
    if not token:
        raise ValueError("Отсутствует токен Telegram (проверь TELEGRAM_BOT_TOKEN / BOT_TOKEN / TG_BOT_TOKEN)")

    updater = Updater(token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CommandHandler("status", cmd_status))
    dp.add_handler(CommandHandler("runall", cmd_runall))

    _setup_scheduler()

    # --- webhook если есть URL, иначе polling ---
    public_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/") or os.getenv("WEBHOOK_URL", "").rstrip("/")
    if public_url:
        port = int(os.getenv("PORT", "10000"))
        listen_addr = "0.0.0.0"
        url_path = token  # уникальный путь
        logger.info("Starting webhook on %s:%s with URL %s/%s", listen_addr, port, public_url, url_path)
        updater.start_webhook(listen=listen_addr, port=port, url_path=url_path)
        updater.bot.setWebhook(f"{public_url}/{url_path}")
        updater.idle()
    else:
        try:
            updater.bot.delete_webhook()
        except Exception:
            pass
        logger.info("Starting long polling...")
        try:
            updater.start_polling(clean=True, timeout=30, read_latency=10.0)
            updater.idle()
        except Conflict as e:
            logger.error("Polling conflict: %s", e)
            logger.error("С тем же токеном работает второй экземпляр. "
                         "Решения: задать WEBHOOK_URL / RENDER_EXTERNAL_URL или перевыпустить токен у @BotFather.")
            # Деградация: оставляем планировщик жить, без чтения апдейтов
            while True:
                time.sleep(60)


if __name__ == "__main__":
    main()
