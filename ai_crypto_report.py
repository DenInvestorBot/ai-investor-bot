# ai_crypto_report.py
# -*- coding: utf-8 -*-
"""
AI Crypto Report — ежедневный отчёт по криптовалютам.
Минимум зависимостей: requests, openai (praw — опционально).
"""

import os
import time
import math
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests

# ---- OpenAI ----
try:
    from openai import OpenAI
    _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    _openai_client = None

# ---- Reddit (опционально) ----
REDDIT_ENABLED = False
try:
    import praw
    REDDIT_ENABLED = True
except Exception:
    REDDIT_ENABLED = False

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
HEADERS = {"Accept": "application/json"}

# ---------------------------
# Простой HTTP с повторами
# ---------------------------
def _get(url: str, params: Optional[Dict[str, Any]] = None, retries: int = 3, timeout: int = 10) -> Any:
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, params=params or {}, timeout=timeout)
            if resp.status_code == 429:
                time.sleep(2 + attempt)
                continue
            if resp.status_code >= 400:
                raise RuntimeError(f"{resp.status_code}: {resp.text[:200]}")
            return resp.json()
        except Exception as e:
            last_err = e
            time.sleep(1 + attempt)
    raise RuntimeError(f"Ошибка запроса {url}: {last_err}")

# ---------------------------
# Источники данных
# ---------------------------
def fetch_market_top(n: int = 60, vs_currency: str = "usd") -> List[Dict[str, Any]]:
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
# Отбор кандидатов
# ---------------------------
def pick_candidates(market: List[Dict[str, Any]], recent: List[Dict[str, Any]], max_out: int = 10) -> List[Dict[str, Any]]:
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
    out, seen = [], set()
    for _, c in scored:
        cid = c.get("id")
        if cid in seen:
            continue
        seen.add(cid)
        out.append(c)
        if len(out) >= max_out:
            break
    return out

# ---------------------------
# Форматирование
# ---------------------------
def _short_num(x: Optional[float]) -> str:
    if x is None:
        return "—"
    try:
        x = float(x)
    except Exception:
        return str(x)
    for suf, val in [("B", 1e9), ("M", 1e6), ("K", 1e3)]:
        if abs(x) >= val:
            return f"{x/val:.2f}{suf}"
    return f"{x:.2f}"

def _fmt_pct(x: Optional[float]) -> str:
    try:
        return f"{float(x):+.2f}%"
    except Exception:
        return "—"

# ---------------------------
# Построение промта
# ---------------------------
def build_ai_prompt(coins: List[Dict[str, Any]], reddit: Dict[str, int]):
    today = datetime.now().strftime("%Y-%m-%d")
    lines = []
    for c in coins:
        name = c.get("name", "")
        t = (c.get("symbol") or "").upper()
        cap = _short_num(c.get("market_cap"))
        vol = _short_num(c.get("total_volume"))
        ch1h = _fmt_pct(c.get("price_change_percentage_1h_in_currency"))
        ch24 = _fmt_pct(c.get("price_change_percentage_24h"))
        ch7d = _fmt_pct(c.get("price_change_percentage_7d_in_currency"))
        r = reddit.get(t, 0) if reddit else 0
        lines.append(f"- {name} ({t}): cap={cap}, vol={vol}, Δ1h={ch1h}, Δ24h={ch24}, Δ7d={ch7d}, reddit={r}")

    system = "Ты — криптоаналитик. Дай краткий анализ, риски и прогноз."
    user = f"Дата: {today}\nМонеты:\n" + "\n".join(lines) + "\n\nВыбери топ-3 и сделай отчёт."
    title = f"**AI Crypto Report — {today}**"
    return system, user, title

# ---------------------------
# Вызов модели
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
# Публичная функция
# ---------------------------
def generate_ai_crypto_report(vs_currency: str = "usd", model: str = "gpt-4.1") -> str:
    market = fetch_market_top(50, vs_currency)
    recent = fetch_recently_added(20)
    candidates = pick_candidates(market, recent)
    tickers = [(c.get("symbol") or "").upper() for c in candidates]
    reddit_counts = fetch_reddit_mentions(tickers) if tickers else {}
    sys_p, user_p, title = build_ai_prompt(candidates, reddit_counts)
    ai_text = call_model(sys_p, user_p, model=model)
    return f"{title}\n\n{ai_text}"

# ---------------------------
# Локальный тест
# ---------------------------
if __name__ == "__main__":
    print(generate_ai_crypto_report())
