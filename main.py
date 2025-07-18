import logging
from telegram import ParseMode
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
import os

from crypto_monitor import run_crypto_analysis, fetch_new_coins, analyze_coin
from ipo_monitor import run_ipo_monitor, fetch_today_ipos
from reddit_monitor import run_reddit_monitor
from telegram import Bot

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = Bot(token=BOT_TOKEN)

def job():
    logger.info("🚀 Запуск мониторинга крипты, IPO и Reddit...")
    run_crypto_analysis()
    run_ipo_monitor()
    run_reddit_monitor()

def send_daily_summary():
    logger.info("📊 Отправка вечерней сводки...")

    # Крипта
    crypto_summary = "🪙 *Крипто-новинки сегодня:*
"
    coins = fetch_new_coins()
    for coin in coins[:3]:
        name, analysis = analyze_coin(coin["id"])
        crypto_summary += f"— *{name}*: {analysis[:200]}...

"

    # IPO
    ipo_summary = "📈 *IPO сегодня:*
"
    ipos = fetch_today_ipos()
    if ipos:
        for ipo in ipos[:3]:
            company = ipo.get("company", "Без названия")
            symbol = ipo.get("symbol", "???")
            exchange = ipo.get("exchange", "??")
            date = ipo.get("date", "")
            ipo_summary += f"— {company} ({symbol}) на {exchange}, дата: {date}
"
    else:
        ipo_summary += "Сегодня IPO не найдено.
"

    message = f"📅 *Сводка на {datetime.now().strftime('%d.%m.%Y')}*

"
    message += crypto_summary + "
" + ipo_summary

    bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN)

def main():
    logger.info("🤖 AI-инвестор бот запущен!")
    scheduler = BlockingScheduler()
    scheduler.add_job(job, 'interval', hours=6)
    scheduler.add_job(send_daily_summary, 'cron', hour=18, minute=0)
    job()  # Первый запуск сразу
    scheduler.start()

if __name__ == "__main__":
    main()
