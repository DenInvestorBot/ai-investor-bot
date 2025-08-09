import os
import re
import traceback
from typing import List, Dict

import praw
from crypto_monitor import send_to_telegram, _escape_markdown

print("📄 [reddit_monitor] Модуль загружен")

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "ai-investor-bot/1.0")

SUBS = [s.strip() for s in os.getenv("REDDIT_SUBS", "wallstreetbets").split(",") if s.strip()]

DEFAULT_TICKERS = "GME,RBNE,TSLA,AAPL,NVDA,MSFT,AMZN,META,NFLX,AMD"
TICKERS: List[str] = [t.strip().upper() for t in os.getenv("REDDIT_TICKERS", DEFAULT_TICKERS).split(",") if t.strip()]

def _compile_patterns(tickers: List[str]) -> Dict[str, re.Pattern]:
    # учитываем $TSLA и границы слова
    return {t: re.compile(rf"\b\$?{re.escape(t)}\b", flags=re.IGNORECASE) for t in tickers}

def _count_mentions_in_text(text: str, patterns: Dict[str, re.Pattern]):
    counts = {}
    for t, pat in patterns.items():
        hits = len(pat.findall(text))
        if hits:
            counts[t] = counts.get(t, 0) + hits
    return counts

def run_reddit_monitor():
    print("🚀 [reddit_monitor] Запуск мониторинга Reddit...")
    if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET):
        msg = "⚠️ Не заданы Reddit креды (REDDIT_CLIENT_ID/SECRET)."
        print(f"[reddit_monitor] {msg}")
        send_to_telegram(_escape_markdown(msg))
        return

    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
            check_for_async=False,
        )
        print("✅ [reddit_monitor] Подключение к Reddit установлено")
    except Exception:
        print("❌ [reddit_monitor] Не удалось создать клиент Reddit:")
        traceback.print_exc()
        send_to_telegram(_escape_markdown("❌ Ошибка Reddit: не удалось инициализировать клиент."))
        return

    patterns = _compile_patterns(TICKERS)
    mention_counts = {}

    try:
        for sub in SUBS:
            print(f"🔎 [reddit_monitor] Читаю сабреддит: r/{sub}")
            try:
                for post in reddit.subreddit(sub).new(limit=100):
                    title = post.title or ""
                    selftext = getattr(post, "selftext", "") or ""
                    text = f"{title}\n{selftext}"
                    local = _count_mentions_in_text(text, patterns)
                    if local:
                        for k, v in local.items():
                            mention_counts[k] = mention_counts.get(k, 0) + v
                print(f"📊 [reddit_monitor] r/{sub}: найдено упоминаний {sum(mention_counts.values())}")
            except Exception:
                print(f"⚠️ [reddit_monitor] Ошибка при обходе r/{sub}:")
                traceback.print_exc()
                continue
    except Exception:
        print("❌ [reddit_monitor] Общая ошибка при сборе данных по Reddit:")
        traceback.print_exc()
        send_to_telegram(_escape_markdown("❌ Ошибка Reddit при сборе данных."))
        return

    if not mention_counts:
        msg = "❗️ В Reddit нет упоминаний из списка тикеров."
        print(f"[reddit_monitor] {msg}")
        send_to_telegram(_escape_markdown(msg))
        return

    top3 = sorted(mention_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    lines = [f"*{_escape_markdown(t)}* — {c} упоминаний" for t, c in top3]
    summary = "📈 *Reddit Топ-тикеры дня:*\n\n" + "\n".join(lines)
    send_to_telegram(summary)
    print(f"✅ [reddit_monitor] Отчёт отправлен. Топ-3: {top3}")
