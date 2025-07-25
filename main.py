import logging
import os
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone

from crypto_monitor import run_crypto_analysis
from ipo_monitor import run_ipo_monitor
from reddit_monitor import run_reddit_monitor

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== Telegram команды =====
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 Привет! Я AI-инвестор бот.\nТвой chat_id: {update.message.chat_id}\nПиши /help для списка команд."
    )

async def help_command(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — Приветствие\n/help — Список команд\n/status — Проверка работоспособности"
    )

async def status(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает. Мониторинг активен.")

def job():
    try:
        logger.info("🚀 Запуск мониторинга крипты, IPO и Reddit...")
        run_crypto_analysis()
        run_ipo_monitor()
        run_reddit_monitor()
    except Exception as e:
        logger.error(f"❌ Ошибка в job(): {e}")

def main():
    logger.info("🤖 AI-инвестор бот запущен!")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))

    scheduler = BackgroundScheduler(timezone=timezone("UTC"))
    scheduler.add_job(job, 'cron', hour=21, minute=0)
    scheduler.start()

    job()  # Первый запуск сразу
    app.run_polling()

if __name__ == "__main__":
    main()
