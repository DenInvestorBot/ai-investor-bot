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


# ---------- Устойчивое разрешение функций из модулей ----------

def _resolve_runner(module_name, preferred=("run_crypto_monitor", "run", "main", "check", "monitor")):
    """
    Пытаемся импортировать модуль и взять одну из функций:
    - сперва exact: run_crypto_monitor  (или другое имя для соответствующего модуля)
    - затем fallback: run / main / check / monitor
    Если ни одной нет — вернём раннер, который просто логирует пропуск.
    """
    try:
        m = importlib.import_module(module_name)
    except Exception as e:
        logger.exception("Не удалось импортировать модуль %s", module_name)
        def _stub():
            logger.error("%s: модуль не импортирован (%s)", module_name, e)
        return _stub

    # Выберем первую доступную функцию
    for name in preferred:
        if hasattr(m, name):
            func = getattr(m, name)
            if callable(func):
                return func

    # Попробуем запустить модуль как скрипт, если функций нет
    def _runner():
        logger.warning("%s: не найдено ожидаемых функций (%s) — пропускаю тик.", module_name, ", ".join(preferred))
    return _runner


# ---------- Команды Telegram ----------

def cmd_start(update, context):
    update.message.reply_text("🤖 AI-Investor-Bot активен! Используй /status.")

def cmd_status(update, context):
    update.message.reply_text("✅ Бот работает. Мониторы: crypto, ipo, reddit, screener.")


# ---------- Точка входа ----------

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

    # 1) Crypto monitor — устойчивое разрешение названия функции
    run_crypto_monitor = _resolve_runner(
        "crypto_monitor",
        preferred=("run_crypto_monitor", "run", "main", "collect_new_coins")  # твои вероятные имена
    )
    scheduler.add_job(run_crypto_monitor, "interval", minutes=30, id="crypto_trending")

    # 2) IPO monitor (если нет функции — тик пропустится без падения)
    run_ipo_monitor = _resolve_runner("ipo_monitor", preferred=("run_ipo_monitor", "run", "main"))
    scheduler.add_job(run_ipo_monitor, "interval", hours=6, id="ipo_monitor")

    # 3) Reddit monitor
    run_reddit_monitor = _resolve_runner("reddit_monitor", preferred=("run_reddit_monitor", "run", "main"))
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
