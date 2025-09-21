# rbne_monitor.py
import os
import json
import time
import hashlib
from datetime import datetime, timezone, timedelta

import feedparser
import praw
import requests
from openai import OpenAI

# =============================
# Конфигурация
# =============================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # твой личный chat_id или канал
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "ai-investor-bot/1.0 by rbne-monitor")

# Ключевые слова для поиска
TICKER = "RBNE"
COMPANY = "Robin Energy"
KEYWORDS = [TICKER, COMPANY.lower(), COMPANY]

# Дедупликация
SEEN_PATH = os.getenv("RBNE_SEEN_PATH", "/tmp/rbne_seen.json")
SEEN_TTL_HOURS = int(os.getenv("RBNE_SEEN_TTL_HOURS", "48"))

# Таймауты
REQUEST_TIMEOUT = 20

client = OpenAI(api_key=OPENAI_API_KEY)

# =============================
# Утилиты
# =============================
def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_seen():
    try:
        with open(SEEN_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    # Очистка старых записей
    cutoff = datetime.now(timezone.utc) - timedelta(hours=SEEN_TTL_HOURS)
    fresh = {}
    for k, v in data.items():
        try:
            ts = datetime.fromisoformat(v.get("ts"))
        except Exception:
            continue
        if ts >= cutoff:
            fresh[k] = v
    if fresh != data:
        _save_seen(fresh)
    return fresh


def _save_seen(data):
    try:
        with open(SEEN_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def _make_id(source: str, url: str, title: str) -> str:
    raw = f"{source}|{url}|{title}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# =============================
# Источники: Reddit + Google News
# =============================
def fetch_reddit(limit_per_sub=15):
    subs = [
        "stocks",
        "wallstreetbets",
        "investing",
        "stockmarket",
        "finance",
    ]
    results = []

    if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET and REDDIT_USER_AGENT):
        return results

    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        ratelimit_seconds=5,
    )

    query = f"(title:{TICKER} OR selftext:{TICKER} OR title:\"{COMPANY}\" OR selftext:\"{COMPANY}\")"

    for sub in subs:
        try:
            for post in reddit.subreddit(sub).search(query=query, sort="new", limit=limit_per_sub):
                title = post.title or ""
                text = post.selftext or ""
                url = f"https://www.reddit.com{post.permalink}"
                results.append({
                    "source": "reddit",
                    "sub": sub,
                    "title": title,
                    "text": text,
                    "url": url,
                    "created_utc": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
                })
        except Exception:
            continue

    return results


def fetch_google_news(max_items=30):
    feed_url = (
        "https://news.google.com/rss/search?q="
        + requests.utils.quote(f"{COMPANY} OR {TICKER}")
        + "&hl=en-US&gl=US&ceid=US:en"
    )
    parsed = feedparser.parse(feed_url)
    items = []
    for e in parsed.entries[:max_items]:
        title = getattr(e, "title", "")
        summary = getattr(e, "summary", "")
        link = getattr(e, "link", "")
        published = getattr(e, "published", None)
        items.append({
            "source": "google_news",
            "title": title,
            "text": summary,
            "url": link,
            "created_utc": published or _now_iso(),
        })
    return items


# =============================
# AI-анализ
# =============================
def analyze_news(items):
    analyzed = []
    for it in items:
        body = (it.get("title", "") + "\n" + it.get("text", "")).strip()
        prompt = (
            "Ты — финансовый аналитик. На входе — короткая новость/пост про компанию Robin Energy (тикер RBNE). "
            "Задача: 1) дай очень краткую выжимку (<=25 слов), 2) оцени тональность: positive/negative/neutral, "
            "3) дай рекомендацию: buy/hold/sell, 4) укажи уверенность (0-100). Верни JSON с ключами: summary, sentiment, action, confidence.\n\n"
            f"Текст:\n{body}"
        )
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)
        except Exception:
            data = {
                "summary": it.get("title", "")[:120],
                "sentiment": "neutral",
                "action": "hold",
                "confidence": 50,
            }
        it.update(data)
        analyzed.append(it)
    return analyzed


# =============================
# Нотификации
# =============================
def send_telegram_message(text: str):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        return r.status_code == 200
    except Exception:
        return False


def format_item(it):
    title = it.get("title", "").strip() or "(без заголовка)"
    url = it.get("url", "")
    source = it.get("source", "?")
    summary = it.get("summary", "")
    sentiment = it.get("sentiment", "neutral")
    action = it.get("action", "hold")
    conf = it.get("confidence", 50)
    created = it.get("created_utc", _now_iso())

    return (
        f"<b>RBNE — новое упоминание</b>\n"
        f"Источник: {source}\n"
        f"Заголовок: {title}\n"
        f"Ссылка: {url}\n"
        f"\n<b>AI-выжимка:</b> {summary}\n"
        f"Тональность: {sentiment}\n"
        f"Рекомендация: <b>{action.upper()}</b> ({conf}%)\n"
        f"Время: {created}"
    )


# =============================
# Основной цикл разовой проверки
# =============================
def run_once():
    seen = _load_seen()

    items = []
    items.extend(fetch_reddit())
    items.extend(fetch_google_news())

    filtered = []
    for it in items:
        blob = (it.get("title", "") + " " + it.get("text", "")).lower()
        if any(k.lower() in blob for k in KEYWORDS):
            filtered.append(it)

    if not filtered:
        return 0

    analyzed = analyze_news(filtered)

    new_count = 0
    for it in analyzed:
        uid = _make_id(it.get("source", "?"), it.get("url", ""), it.get("title", ""))
        if uid in seen:
            continue
        message = format_item(it)
        ok = send_telegram_message(message)
        if ok:
            new_count += 1
            seen[uid] = {"ts": _now_iso(), "url": it.get("url")}

    _save_seen(seen)
    return new_count


if __name__ == "__main__":
    count = run_once()
    print(f"RBNE monitor sent {count} new items")
