import os
import pytz
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

from ipo_monitor import run_ipo_monitor
from crypto_monitor import run_crypto_analysis

# Переменные окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Планировщик задач (21:00 UTC)
scheduler = BackgroundScheduler(timezone=pytz.UTC)

@scheduler.scheduled_job('cron', hour=21, minute=0)
def scheduled_tasks():
    print("⏰ Планировщик: запуск анализа...")
    run_ipo_monitor()
    run_crypto_analysis()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я AI-инвестор-бот.\nПиши /status чтобы проверить, всё ли работает.")

# Команда /status
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот активен. Следующий анализ будет в 21:00 по UTC.")

# Фоновый запуск планировщика
def run_scheduler():
    print("✅ Планировщик запущен")
    scheduler.start()

# Основной запуск Telegram-бота
def run_bot():
    print("🤖 Запуск Telegram-бота (режим polling)")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))

    app.run_polling()

if __name__ == "__main__":
    # Запускаем планировщик в отдельном потоке
    threading.Thread(target=run_scheduler).start()
    # Запускаем Telegram-бота
    run_bot()
