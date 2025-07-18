import logging
import os
import requests
import openai
from telegram import Bot

REDDIT_KEYWORDS = ["GME", "RBNE", "TSLA", "AAPL", "NVDA", "MSFT", "AMZN", "META", "NFLX", "AMD"]

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

logger = logging.getLogger(__name__)

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
