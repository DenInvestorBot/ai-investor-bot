# ai_crypto_report.py
# -*- coding: utf-8 -*-
"""
AI Crypto Report — ежедневный отчёт по криптовалютам.
1) Берёт данные с CoinGecko (топ монеты + недавно добавленные)
2) Опционально собирает упоминания Reddit
3) Формирует промт и получает аналитический отчёт от OpenAI
4) Возвращает результат в Markdown для отправки в Telegram
"""

import os
import math
import time
import textwrap
from datetime import datetime
from typing import List, Dict, Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --- OpenAI клиент ---
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
# HTTP helper
# ---------------------------
class HttpError(Exception):
    pass

@retry(reraise=True, stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=1, max=5),
       retry=retry_if_exception_type((HttpError, requests.RequestException)))
def _get(url: str, params: Dict[str, Any] = None) -> Any:
    resp = requests.get(url, headers=HEADERS, params=params or {}, timeout=10)
    if resp.status_code == 429:
        time.sleep(2)
        raise HttpError("429 Too Many Requests")
    if resp.status_code >= 400:
        raise HttpError(f"{resp.status_code}: {resp.text[:100]}")
    return resp.json()

# ---------------------------
# Data sources
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
        for sub in reddit.subreddit(subreddit).new(limit=limit):
            text = f"{sub.title} {sub.selftext or ''}".upper()
            for t in counts:
                if f" {t} " in " " + text + " ":
                    counts[t] += 1
    except Exception:
        pass
    return counts

# ---------------------------
# Candidate selection
# ---------------------------
def pick_candidates(market: List[Dict[str, Any]], recent: List[Dict[str, Any]], max_out: int = 8) -> List[Dict[str, Any]]:
    scored = []
    for coin in market:
        vol = coin.get("total_volume") or 0
        cap = coin.get("market_cap") or 0
        ch24 = coin.get("price_change_percentage_24h") or 0
        ch7d = coin.get("price_change_percentage_7d_in_currency") or 0
        score = (ch24 * 0.6) + (ch7d * 0.4) + math.log10(vol + 1) + math.log10(cap + 1)
        scored.append((score, coin))
    for coin in recent:
        scored.append((5.0, coin))  # бонус новым
    scored.sort(key=lambda x: x[0], reverse=True)
    uniq, picked = {}, []
    for _, c in scored:
        cid = c.get("id")
        if cid in uniq:
            continue
        uniq[cid] = True
        picked.append(c)
        if len(picked) >= max_out:
            break
    return picked

# ---------------------------
# Prompt builder
# ---------------------------
def _short(x: float) -> str:
    if x is None:
        return "—"
    try:
        x = float(x)
    except:
        return str(x)
    for s, v in [("B", 1e9), ("M", 1e6), ("K", 1e3)]:
        if abs(x) >= v:
            return f"{x/v:.1f}{s}"
    return f"{x:.1f}"

def build_prompt(coins: List[Dict[str, Any]], reddit: Dict[str, int]) -> (str, str, str):
    today = datetime.now().strftime("%Y-%m-%d")
    lines = []
    for c in coins:
        name = c.get("name", "")
        t = (c.get("symbol") or "").upper()
        cap = _short(c.get("market_cap"))
        vol = _short(c.get("total_volume"))
        ch1h = c.get("price_change_percentage_1h_in_currency")
        ch24 = c.get("price_change_percentage_24h")
        ch7d = c.get("price_change_percentage_7d_in_currency")
        r = reddit.get(t, 0) if reddit else 0
        lines.append(f"- {name} ({t}): cap={cap}, vol24h={vol}, Δ1h={ch1h} Δ24h={ch24} Δ7d={ch7d}, reddit={r}")
    system = "Ты — опытный криптоаналитик. Дай краткий анализ, риски и прогноз для инвестора."
    user = f"Дата: {today}\nМонеты:\n" + "\n".join(lines) + \
           "\n\nВыбери топ-3, укажи потенциал роста %, факторы, buy/sell уровни, риск, рекомендацию. Итог — краткое резюме."
    title = f"**AI Crypto Report — {today}**"
    return system, user, title

# ---------------------------
# OpenAI call
# ---------------------------
def call_model(system_prompt: str, user_prompt: str, model: str = "gpt-4.1") -> str:
    if _openai_client is None:
        raise RuntimeError("OpenAI client не инициализирован. Проверь OPENAI_API_KEY.")
    resp = _openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=900,
    )
    return resp.choices[0].message.content.strip()

# ---------------------------
# Public API
# ---------------------------
def generate_ai_crypto_report(vs_currency: str = "usd", model: str = "gpt-4.1") -> str:
    market = fetch_market_top(60, vs_currency)
    recent = fetch_recently_added(20)
    candidates = pick_candidates(market, recent)
    tickers = [(c.get("symbol") or "").upper() for c in candidates]
    reddit_counts = fetch_reddit_mentions(tickers) if tickers else {}
    sys_p, user_p, title = build_prompt(candidates, reddit_counts)
    ai_text = call_model(sys_p, user_p, model=model)
    return f"{title}\n\n{ai_text}"

# ---------------------------
# CLI test
# ---------------------------
if __name__ == "__main__":
    print(generate_ai_crypto_report())
