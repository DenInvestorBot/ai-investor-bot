import logging
import os
import requests
import openai
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

REDDIT_KEYWORDS = ["GME", "RBNE", "TSLA", "AAPL", "NVDA", "MSFT", "AMZN", "META", "NFLX", "AMD"]

# ===== Reddit Монитор =====
def fetch_reddit_posts():
    url = "https://www.reddit.com/r/wallstreetbets/new.json?limit=100"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()["data"]["children"]
        else:
            logger.warning("⚠️ Ошибка запроса Reddit: %s", response.status_code)
    except Exception as e:
        logger.error("❌ Ошибка получения данных с Reddit: %s", e)
    return []

def extract_mentions(posts):
    mention_counts = {}
    for post in posts:
        text = post["data"].get("title", "") + " " + post["data"].get("selftext", "")
        for keyword in REDDIT_KEYWORDS:
            if keyword.upper() in text.upper():
                mention_counts[keyword] = mention_counts.get(keyword, 0) + 1
    return sorted(mention_counts.items(), key=lambda x: x[1], reverse=True)

def analyze_sentiment(ticker, mentions):
    prompt = (
        f"Reddit обсуждение тикера {ticker} упоминается {mentions} раз.\n"
        f"Проанализируй общий тон обсуждений и инвестиционное настроение."
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ Ошибка анализа тональности {ticker}: {e}")
        return f"Ошибка анализа для {ticker}."

def run_reddit_monitor():
    posts = fetch_reddit_posts()
    if not posts:
        bot.send_message(chat_id=CHAT_ID, text="⚠️ Нет свежих данных с Reddit.")
        return

    mentions = extract_mentions(posts)
    if not mentions:
        bot.send_message(chat_id=CHAT_ID, text="❗️ Ничего не обсуждается из заданных тикеров.")
        return

    summary = "📈 *Reddit Топ-тикеры дня:*\n"
    for ticker, count in mentions[:3]:
        sentiment = analyze_sentiment(ticker, count)
        summary += f"\n*{ticker}* — {count} упоминаний\n{sentiment}\n"

    bot.send_message(chat_id=CHAT_ID, text=summary, parse_mode="Markdown")

# ===== Команды Telegram =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я AI-инвестор бот. Пиши /help для списка команд.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
/start — Приветствие
/help — Список команд
/status — Проверка работоспособности
    """)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает. Мониторинг активен.")

# ===== Планировщик =====
def job():
    try:
        logger.info("🚀 Запуск мониторинга крипты, IPO и Reddit...")
        run_reddit_monitor()
    except Exception as e:
        logger.error(f"❌ Ошибка в job(): {e}")

# ===== Запуск приложения =====
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
