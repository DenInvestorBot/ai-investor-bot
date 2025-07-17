import requests
import datetime
import os
import openai
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

SUBREDDITS = ["stocks", "wallstreetbets", "investing"]
TICKERS = ["TSLA", "AAPL", "AMZN", "META", "MSFT", "GME", "RBNE", "NVDA", "GOOGL", "NFLX", "BRK.B", "AMD"]

def fetch_reddit_posts():
    url = f"https://api.pushshift.io/reddit/search/submission/?subreddit={','.join(SUBREDDITS)}&sort=desc&size=20"
    try:
        res = requests.get(url)
        if res.ok:
            return res.json().get("data", [])
    except:
        return []

def analyze_with_gpt(text):
    prompt = f"Проанализируй пост и определи: это паника, хайп или анализ?\n\n{text}"
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120
        )
        return res.choices[0].message["content"].strip()
    except:
        return "⚠️ Не удалось получить анализ от GPT."

def run_reddit_monitor():
    posts = fetch_reddit_posts()
    for post in posts:
        title = post.get("title", "")
        body = post.get("selftext", "")
        url = post.get("full_link", "")
        text = f"{title}\n\n{body}"
        tickers_found = [t for t in TICKERS if t in text.upper()]
        if tickers_found:
            summary = analyze_with_gpt(text[:1000])
            message = f"📢 Обнаружено упоминание: {', '.join(tickers_found)}\n\n🔗 {url}\n\n🧠 GPT-анализ:\n{summary}"
            bot.send_message(chat_id=CHAT_ID, text=message)

if __name__ == "__main__":
    run_reddit_monitor()
