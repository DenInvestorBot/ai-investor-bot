import os
import re
import traceback
from typing import List, Dict, Tuple

import praw
from openai import OpenAI

from crypto_monitor import send_to_telegram, _escape_markdown

print("[reddit_monitor] module loaded")

# --- ENV ---
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "ai-investor-bot/1.0")

SUBS = [s.strip() for s in os.getenv("REDDIT_SUBS", "wallstreetbets").split(",") if s.strip()]
DEFAULT_TICKERS = "GME,RBNE,TSLA,AAPL,NVDA,MSFT,AMZN,META,NFLX,AMD"
TICKERS: List[str] = [t.strip().upper() for t in os.getenv("REDDIT_TICKERS", DEFAULT_TICKERS).split(",") if t.strip()]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUMMARIZE = os.getenv("REDDIT_SUMMARIZE", "1")  # "1"=on, "0"=off
client = OpenAI(api_key=OPENAI_API_KEY) if (OPENAI_API_KEY and SUMMARIZE != "0") else None

# --- Helpers ---
def _compile_patterns(tickers: List[str]) -> Dict[str, re.Pattern]:
    # Учитываем $TSLA и границы слова
    return {t: re.compile(rf"\b\$?{re.escape(t)}\b", flags=re.IGNORECASE) for t in tickers}

def _count_mentions_and_collect(
    text: str,
    patterns: Dict[str, re.Pattern],
    store: Dict[str, List[str]],
    title: str,
    limit_per_ticker: int = 12,
) -> Dict[str, int]:
    counts = {}
    for t, pat in patterns.items():
        hits = len(pat.findall(text))
        if hits:
            counts[t] = counts.get(t, 0) + hits
            # копим заголовки для последующего резюме
            if len(store[t]) < limit_per_ticker:
                # коротко нормализуем заголовки
                cleaned = re.sub(r"\s+", " ", title).strip()
                store[t].append(cleaned)
    return counts

def _summarize_ticker(ticker: str, titles: List[str]) -> str:
    """Короткое резюме обсуждений тикера по заголовкам постов."""
    if not titles:
        return "Обсуждений мало/не выявлено."
    if not client:
        # Фоллбэк без AI: покажем 2–3 характерных заголовка
        sample = "; ".join(titles[:3])
        return f"Главное по заголовкам: {sample}"

    joined = "\n".join(f"- {t}" for t in titles[:10])
    prompt = (
        "Суммируй в 1–2 кратких пунктах (на русском), что именно обсуждают на Reddit про тикер. "
        "Говори по делу: драйверы роста/падения, новости, отчёты, слухи, стратегия. "
        "Используй максимум 220 символов на всё резюме.\n\n"
        f"Тикер: {ticker}\n"
        f"Заголовки постов:\n{joined}"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=120,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text
    except Exception:
        traceback.print_exc()
        sample = "; ".join(titles[:3])
        return f"Главное по заголовкам: {sample}"

# --- Main ---
def run_reddit_monitor():
    print("[reddit_monitor] start")
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
        print("[reddit_monitor] Reddit client OK")
    except Exception:
        print("[reddit_monitor] failed to create Reddit client:")
        traceback.print_exc()
        send_to_telegram(_escape_markdown("❌ Ошибка Reddit: не удалось инициализировать клиент."))
        return

    patterns = _compile_patterns(TICKERS)
    mention_counts: Dict[str, int] = {t: 0 for t in TICKERS}
    titles_store: Dict[str, List[str]] = {t: [] for t in TICKERS}

    try:
        for sub in SUBS:
            print(f"[reddit_monitor] scanning r/{sub}")
            for post in reddit.subreddit(sub).new(limit=120):
                title = (post.title or "").strip()
                selftext = (getattr(post, "selftext", "") or "").strip()
                text = f"{title}\n{selftext}"
                local = _count_mentions_and_collect(text, patterns, titles_store, title)
                for k, v in local.items():
                    mention_counts[k] = mention_counts.get(k, 0) + v
    except Exception:
        print("[reddit_monitor] error while collecting posts:")
        traceback.print_exc()
        send_to_telegram(_escape_markdown("❌ Ошибка Reddit при сборе данных."))
        return

    # убираем нули
    mention_counts = {k: v for k, v in mention_counts.items() if v > 0}
    if not mention_counts:
        msg = "❗️ В Reddit нет упоминаний из списка тикеров."
        print(f"[reddit_monitor] {msg}")
        send_to_telegram(_escape_markdown(msg))
        return

    # Топ-3 по упоминаниям
    top3: List[Tuple[str, int]] = sorted(mention_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    # Формируем резюме для каждого
    lines = ["📈 *Reddit Топ-тикеры дня:*", ""]
    for ticker, count in top3:
        summary = _summarize_ticker(ticker, titles_store.get(ticker, []))
        line = f"*{_escape_markdown(ticker)}* — {count} упоминаний\n" \
               f"{_escape_markdown(summary)}"
        lines.append(line)
        lines.append("")  # пустая строка между тикерами

    msg = "\n".join(lines).strip()
    send_to_telegram(msg)
    print(f"[reddit_monitor] report sent. top3={top3}")
