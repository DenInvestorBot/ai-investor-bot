import os
from apscheduler.schedulers.blocking import BlockingScheduler
from crypto_monitor import run_crypto_analysis
from ipo_monitor import main as run_ipo_analysis
# from reddit_monitor import run_reddit_analysis (будет позже)
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = Bot(token=BOT_TOKEN)

scheduler = BlockingScheduler()

# Запуск анализа криптовалют — каждый день в 10:00
@scheduler.scheduled_job('cron', hour=10, minute=0)
def crypto_task():
    run_crypto_analysis()

# Запуск анализа IPO — каждый день в 11:00
@scheduler.scheduled_job('cron', hour=11, minute=0)
def ipo_task():
    run_ipo_analysis()

# Вечерняя сводка в 21:00
@scheduler.scheduled_job('cron', hour=21, minute=0)
def summary():
    bot.send_message(chat_id=CHAT_ID, text="📊 Вечерняя сводка инвест-сигналов. (тест — пока без Reddit)")

if __name__ == "__main__":
    scheduler.start()
