import logging
import os
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone

from crypto_monitor import run_crypto_analysis
from ipo_monitor import run_ipo_monitor
from reddit_monitor import run_reddit_monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=BOT_TOKEN)

# ===== Telegram команды =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 Привет! Я AI-инвестор бот.\nТвой chat_id: {update.message.chat_id}\nПиши /help для списка команд."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — Приветствие\n/help — Список команд\n/status — Проверка работоспособности"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    # Тестовая рассылка каждые 2 минуты (после проверки можешь убрать эту строку!)
    scheduler.add_job(job, 'interval', minutes=2)
    # Основная рассылка (раз в день в 21:00 UTC)
    scheduler.add_job(job, 'cron', hour=21, minute=0)
    scheduler.start()

    job()  # Первый запуск сразу
    app.run_polling()

if __name__ == "__main__":
    main()
from telegram import Bot
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=BOT_TOKEN)
bot.send_message(chat_id=CHAT_ID, text="👋 Тестовое сообщение прямо при старте!")
