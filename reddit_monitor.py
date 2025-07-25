import os
import praw
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

bot = Bot(token=BOT_TOKEN)

REDDIT_KEYWORDS = ["GME", "RBNE", "TSLA", "AAPL", "NVDA", "MSFT", "AMZN", "META", "NFLX", "AMD"]

def run_reddit_monitor():
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )
    posts = reddit.subreddit("wallstreetbets").new(limit=100)
    mention_counts = {}
    for post in posts:
        text = post.title + " " + getattr(post, "selftext", "")
        for keyword in REDDIT_KEYWORDS:
            if keyword.upper() in text.upper():
                mention_counts[keyword] = mention_counts.get(keyword, 0) + 1
    if not mention_counts:
        bot.send_message(chat_id=CHAT_ID, text="❗️ Ничего не обсуждается из заданных тикеров.")
        return
    summary = "📈 *Reddit Топ-тикеры дня:*\n"
    for ticker, count in sorted(mention_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
        summary += f"\n*{ticker}* — {count} упоминаний"
    bot.send_message(chat_id=CHAT_ID, text=summary, parse_mode="Markdown")
