import os
import requests
import openai
from telegram import Bot

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

# Тикеры, которые отслеживаем
TICKERS = ["GME", "RBNE", "TSLA", "NVDA", "AAPL"]

def fetch_reddit_mentions():
    try:
        headers = {"User-Agent": "ai-investor-bot"}
        url = f"https://api.pushshift.io/reddit/search/comment/?q={'|'.join(TICKERS)}&subreddit=wallstreetbets&size=10&sort=desc"
        response = requests.get(url, headers=headers)
        if response.ok:
            return response.json().get("data", [])
    except Exception as e:
        print("Ошибка при запросе к Reddit:", e)
    return []

def analyze_reddit_post(post_text):
    prompt = f"На Reddit появилось обсуждение: {post_text[:700]}\n\nСделай краткий инвестиционный вывод. Есть ли интерес к акции, и стоит ли обратить внимание инвестору?"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # временно gpt-3.5
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return "⚠️ Ошибка анализа GPT."

def send_to_telegram(message):
    bot.send_message(chat_id=CHAT_ID, text=message)

def run_reddit_monitor():
    posts = fetch_reddit_mentions()
    for post in posts:
        body = post.get("body", "")
        if any(ticker in body.upper() for ticker in TICKERS):
            analysis = analyze_reddit_post(body)
            message = f"📢 Reddit сигнал:\n{body[:300]}...\n\n🧠 GPT-анализ:\n{analysis}"
            send_to_telegram(message)
            break  # отправим только 1 пост за раз, чтобы не спамить
