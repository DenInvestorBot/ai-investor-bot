import praw
from telegram import Bot

BOT_TOKEN = "7913819667:AAFDNAsoSgwA6Y_eTc1zuaP1LoLWNJTLJcQ"  # Подставь свой токен
CHAT_ID = 1634571706  # Твой chat_id

REDDIT_CLIENT_ID = "REDDIT_CLIENT_ID"  # Подставь свой reddit client_id
REDDIT_CLIENT_SECRET = "REDDIT_CLIENT_SECRET"  # Подставь свой reddit client_secret
REDDIT_USER_AGENT = "ai-investor-bot/1.0 by u/According-Stable4487"

bot = Bot(token=BOT_TOKEN)

REDDIT_KEYWORDS = ["GME", "RBNE", "TSLA", "AAPL", "NVDA", "MSFT", "AMZN", "META", "NFLX", "AMD"]

def run_reddit_monitor():
    bot.send_message(chat_id=CHAT_ID, text="📈 Тестовое сообщение от reddit_monitor!")  # <-- Явная проверка
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
