import os
import re
import requests
import praw
from typing import List

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "0"))

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "ai-investor-bot/1.0")

from crypto_monitor import send_to_telegram, _escape_markdown

# Можно задать через .env, например: "wallstreetbets,stocks,investing,Superstonk"
SUBS = [s.strip() for s in os.getenv("REDDIT_SUBS", "wallstreetbets").split(",") if s.strip()]

# Тикеры через .env, например: "GME,RBNE,TSLA,AAPL,NVDA,MSFT,AMZN,META,NFLX,AMD"
DEFAULT_TICKERS = "GME,RBNE,TSLA,AAPL,NVDA,MSFT,AMZN,META,NFLX,AMD"
TICKERS: List[str] = [t.strip().upper() for t in os.getenv("REDDIT_TICKERS", DEFAULT_TICKERS).split(",") if t.strip()]

def _compile_patterns(tickers: List[str]):
    """
    Учитываем $TSLA и границы слов: \b(\$?TSLA)\b
    """
    patterns = {}
    for t in tickers:
        patterns[t] = re.compile(rf"\b\$?{re.escape(t)}\b", flags=re.IGNORECASE)
    return patterns

def _count_mentions_in_text(text: str, patterns):
    counts = {}
    for t, pat in patterns.items():
        hits = len(pat.findall(text))
        if hits:
            counts[t] = counts.get(t, 0) + hits
    return counts

def run_reddit_monitor():
    if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET):
        send_to_telegram(_escape_markdown("⚠️ Не заданы Reddit креды (REDDIT_CLIENT_ID/SECRET)."))
        return

    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        check_for_async=False,
    )

    patterns = _compile_patterns(TICKERS)
    mention_counts = {}

    try:
        for sub in SUBS:
            # Берём ~100 свежих постов в каждом сабе
            for post in reddit.subreddit(sub).new(limit=100):
                title = post.title or ""
                selftext = getattr(post, "selftext", "") or ""
                text = f"{title}\n{selftext}"
                local = _count_mentions_in_text(text, patterns)
                for k, v in local.items():
                    mention_counts[k] = mention_counts.get(k, 0) + v
    except Exception as e:
        send_to_telegram(_escape_markdown(f"❌ Ошибка Reddit: {e}"))
        return

    if not mention_counts:
        send_to_telegram(_escape_markdown("❗️ В Reddit нет упоминаний из списка тикеров."))
        return

    top3 = sorted(mention_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    lines = [f"*{_escape_markdown(t)}* — {c} упоминаний" for t, c in top3]
    summary = "📈 *Reddit Топ-тикеры дня:*\n\n" + "\n".join(lines)
    send_to_telegram(summary)
