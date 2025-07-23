import logging
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone

from crypto_monitor import run_crypto_analysis
from ipo_monitor import run_ipo_monitor
from reddit_monitor import run_reddit_monitor

BOT_TOKEN = "7913819667:AAGf0vL8sX7zRnwozm7AFhEyHVN0plMOjus"  # Подставь свой актуальный токен
CHAT_ID = 1634571706  # Жестко твой chat_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        bot.send_message(chat_id=CHAT_ID, text="👋 Тестовое сообщение от планировщика!")  # <-- Явная проверка
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
    scheduler.add_job(job, 'interval', minutes=2)
    scheduler.add_job(job, 'cron', hour=21, minute=0)
    scheduler.start()

    bot.send_message(chat_id=CHAT_ID, text="👋 Тестовое сообщение прямо при старте!")  # <-- Ещё одна явная проверка

    job()  # Первый запуск сразу
    app.run_polling()

if __name__ == "__main__":
    main()
