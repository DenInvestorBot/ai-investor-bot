import os
import logging
from collections import Counter
from typing import List, Dict, Any
import requests

log = logging.getLogger(__name__)

SUBREDDITS = os.getenv("SUBREDDITS", "wallstreetbets,stocks,CryptoCurrency").split(",")
TICKERS = [t.strip().upper() for t in os.getenv("TICKERS", "GME,RBNE,BTC,ETH,NVDA,TSLA").split(",") if t.strip()]
LIMIT = int(os.getenv("REDDIT_LIMIT", "50"))

def _send_telegram(text: str) -> None:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TG_BOT_TOKEN"))
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or os.getenv("TG_CHAT_ID"))
    if not (token and chat_id):
        log.info("Reddit: TG token/chat_id не заданы — пропускаю отправку")
        return
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
                          timeout=15)
        r.raise_for_status()
    except requests.RequestException:
        log.exception("Reddit: не удалось отправить сообщение в Telegram")

def _fetch_subreddit_json(sub: str) -> List[Dict[str, Any]]:
    url = f"https://www.reddit.com/r/{sub}/new.json?limit={LIMIT}"
    try:
        r = requests.get(url, headers={"User-Agent": "ai-investor-bot/reddit/1.0"}, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data.get("data", {}).get("children", [])
    except requests.RequestException:
        log.exception("Reddit fetch failed for /r/%s", sub)
        return []

def _count_tickers_in_posts(posts: List[Dict[str, Any]]) -> Counter:
    cnt = Counter()
    for p in posts:
        d = p.get("data", {})
        title = (d.get("title") or "").upper()
        selftext = (d.get("selftext") or "").upper()
        text = f"{title} {selftext}"
        for t in TICKERS:
            if f"${t}" in text or f" {t} " in f" {text} ":
                cnt[t] += 1
    return cnt

def run_reddit_monitor():
    total = Counter()
    for sub in SUBREDDITS:
        posts = _fetch_subreddit_json(sub.strip())
        total.update(_count_tickers_in_posts(posts))

    if not total:
        log.info("Reddit: нет упоминаний по заданным тикерам")
        return

    top = total.most_common(10)
    lines = [f"• <b>{t}</b>: {c}" for t, c in top]
    text = "📈 Reddit: топ упоминаемых тикеров за ~последние посты\n" + "\n".join(lines)
    log.info(text.replace("\n", " | "))
    _send_telegram(text)

def run():
    run_reddit_monitor()

def main():
    run_reddit_monitor()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_reddit_monitor()
