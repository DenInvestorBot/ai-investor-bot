# ai_crypto_report.py
# -*- coding: utf-8 -*-
"""
AI Crypto Report — Ежедневный отчёт по криптовалютам.
1) Берёт данные с CoinGecko (топ монеты + недавно добавленные)
2) Опционально собирает упоминания Reddit
3) Формирует промт и получает аналитический отчёт от OpenAI
4) Возвращает результат в Markdown для отправки в Telegram

Зависимости:
    pip install requests tenacity openai praw
"""

import os
import math
import time
import textwrap
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --- OpenAI client ---
try:
    from openai import OpenAI
    _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    _openai_client = None

# --- Reddit (опционально) ---
REDDIT_ENABLED = False
try:
    import praw
    REDDIT_ENABLED = True
except Exception:
    REDDIT_ENABLED = False

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
HEADERS = {"Accept": "application/json"}

# ---------------------------
# HTTP helpers
# ---------------------------
class HttpError(Exception):
    pass

@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=0.8, min=0.8, max=6),
    retry=retry_if_exception_type((HttpError, requests.RequestException)),
)
def _get(url: str, params: Dict[str, Any] = None) -> Any:
    resp = requests.get(url, headers=HEADERS, params=params or {}, timeout=15)
    if resp.status_code == 429:
        time.sleep(2.5)
        raise HttpError(f"429: rate limited {url}")
    if resp.status_code >= 400:
        raise HttpError(f"{resp.status_code}: {resp.text[:200]}")
    return resp.json()

# ---------------------------
# Data collection
# ---------------------------
def fetch_market_top(n: int = 50, vs_currency: str = "usd") -> List[Dict[str, Any]]:
    return _get(
        f"{COINGECKO_BASE}/coins/markets",
        params={
            "vs_currency": vs_currency,
            "order": "market_cap_desc",
            "per_page": min(n, 250),
            "page": 1,
            "price_change_percentage": "1h,24h,7d",
            "sparkline": False,
        },
    )

def fetch_recently_added(limit: int = 20) -> List[Dict[str, Any]]:
    return _get(
        f"{COINGECKO_BASE}/coins/markets",
        params={
            "vs_currency": "usd",
            "order": "gecko_desc",
            "per_page": min(limit, 100),
            "page": 1,
            "sparkline": False,
        },
    )

def fetch_reddit_mentions(tickers: List[str], subreddit: str = "CryptoCurrency", limit: int = 80) -> Dict[str, int]:
    if not REDDIT_ENABLED:
        return {}
    cid = os.getenv("REDDIT_CLIENT_ID")
    secret = os.getenv("REDDIT_CLIENT_SECRET")
    ua = os.getenv("REDDIT_USER_AGENT", "ai-investor-bot/1.0")
    if not (cid and secret and ua):
        return {}
    reddit = praw.Reddit(client_id=cid, client_secret=secret, user_agent=ua)
    counts = {t.upper(): 0 for t in tickers}
    try:
        for submission in reddit.subreddit(subreddit).new(limit=limit):
            hay = f"{submission.title} {submission.selftext or ''}".upper()
            for t in counts:
                if f" {t} " in " " + hay + " ":
                    counts[t] += 1
    except Exception:
        pass
    return counts

# ---------------------------
# Candidate selection
# ---------------------------
def pick_candidates(market: List[Dict[str, Any]], recent: List[Dict[str, Any]], max_out: int = 8) -> List[Dict[str, Any]]:
    scored = []
    for coin in market[:200]:
        vol = coin.get("total_volume") or 0
        cap = coin.get("market_cap") or 0
        ch24 = coin.get("price_change_percentage_24h") or 0.0
        ch7d = coin.get("price_change_percentage_7d_in_currency") or 0.0
        score = (ch24 * 0.6) + (ch7d * 0.4) + (math.log10(vol + 1) * 2) + (math.log10(cap + 1))
        scored.append((score, coin))
    for coin in recent:
        scored.append((5.0, coin))  # бонус свежим
    scored.sort(key=lambda x: x[0], reverse=True)
    uniq, picked = {}, []
    for _, c in scored:
        key = c.get("id")
        if key in uniq:
            continue
        uniq[key] = True
        picked.append(c)
        if len(picked) >= max_out:
            break
    return picked

# ---------------------------
# Prompt building
# ---------------------------
def _short_num(x: Optional[float]) -> str:
    if x is None:
        return "—"
    try:
        x = float(x)
    except Exception:
        return str(x)
    units = [("", 1), ("K", 1e3), ("M", 1e6), ("B", 1e9)]
    for suf, val in reversed(units):
        if abs(x) >= val:
            return f"{x/val:.2f}{suf}"
    return f"{x:.2f}"

def build_ai_prompt(coins: List[Dict[str, Any]], reddit_mentions: Dict[str, int]) -> (str, str, str):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = []
    for c in coins:
        name = c.get("name", "")
        ticker = (c.get("symbol") or "").upper()
        cap = _short_num(c.get("market_cap"))
        vol = _short_num(c.get("total_volume"))
        ch1h = c.get("price_change_percentage_1h_in_currency")
        ch24 = c.get("price_change_percentage_24h")
        ch7d = c.get("price_change_percentage_7d_in_currency")
        reddit = reddit_mentions.get(ticker, 0) if reddit_mentions else 0
        lines.append(
            f"- {name} ({ticker}): cap={cap}, vol24h={vol}, Δ1h={ch1h:.2f}% | Δ24h={ch24:.2f}% | Δ7d={ch7d if isinstance(ch7d,(int,float)) else 0:.2f}%, reddit_mentions={reddit}"
        )
    system = textwrap.dedent("""\
        Ты — профессиональный криптоаналитик с 10+ годами опыта.
        Анализируй рынок, оценивай риск, ликвидность, новости и соцсигналы.
        Не давай финансовых гарантий, пиши чётко и структурированно.
    """).strip()
    user = textwrap.dedent(f"""\
        Дата отчёта: {today}
        Ниже — сводка монет с метриками рынка и упоминаниями Reddit (если есть).
        Задача:
          1) Выбери топ-3 монеты с потенциалом на 1–4 недели.
          2) Для каждой: факторы роста, уровни buy/sell, риск (низкий/средний/высокий), спекулятивность.
          3) Верни: краткий отчёт → таблицу (тикер, потенциал %, факторы, buy/sell, риск, рекомендация) → финальное резюме.

        Данные:
        {chr(10).join(lines)}
    """).strip()
    title = f"**AI Crypto Report — {today}**"
    return system, user, title

# ---------------------------
# AI call
# ---------------------------
def call_model(system_prompt: str, user_prompt: str, model: str = "gpt-4.1") -> str:
    if _openai_client is None:
        raise RuntimeError("OpenAI client не инициализирован. Проверь OPENAI_API_KEY.")
    resp = _openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}],
        temperature=0.2,
        max_tokens=1200,
    )
    return resp.choices[0].message.content.strip()

# ---------------------------
# Public API
# ---------------------------
def generate_ai_crypto_report(vs_currency: str = "usd", model: str = "gpt-4.1") -> str:
    market = fetch_market_top(100, vs_currency=vs_currency)
    recent = fetch_recently_added(20)
    candidates = pick_candidates(market, recent, max_out=10)
    tickers = [(c.get("symbol") or "").upper() for c in candidates if c.get("symbol")]
    reddit_counts = fetch_reddit_mentions(tickers) if tickers else {}
    system_prompt, user_prompt, title = build_ai_prompt(candidates, reddit_counts)
    ai_text = call_model(system_prompt, user_prompt, model=model)
    return f"{title}\n\n{ai_text}"

# ---------------------------
# CLI test
# ---------------------------
if __name__ == "__main__":
    print(generate_ai_crypto_report())
