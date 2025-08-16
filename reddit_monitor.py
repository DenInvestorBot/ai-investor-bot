# reddit_monitor.py
import os
import asyncio
import logging
import random
from typing import List, Dict, Any
from urllib.parse import quote_plus

import httpx

log = logging.getLogger(__name__)

# Настройки по ENV
DEFAULT_TICKERS = ["GME", "RBNE"]
TICKERS: List[str] = [
    t.strip().upper()
    for t in os.getenv("REDDIT_TICKERS", ",".join(DEFAULT_TICKERS)).split(",")
    if t.strip()
]
REDDIT_TIME = os.getenv("REDDIT_TIME", "day")  # day|week|month|year|all
REDDIT_SEARCH_LIMIT = int(os.getenv("REDDIT_SEARCH_LIMIT", "5"))  # сколько заголовков подтягивать
UA = {"User-Agent": "ai-investor-bot/1.0 (+reddit signals)"}

BASE = "https://www.reddit.com/search.json"
TIMEOUT = httpx.Timeout(20)

async def _get_json(url: str, *, retries: int = 3) -> Dict[str, Any]:
    """
    Надёжный GET c бэкоффом и поддержкой Retry-After на 429.
    """
    delay = 1.0
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, headers=UA, http2=True) as client:
                r = await client.get(url)
                if r.status_code == 429:
                    ra = r.headers.get("Retry-After")
                    try:
                        wait_s = float(ra) if ra else delay + random.random()
                    except ValueError:
                        wait_s = delay + random.random()
                    log.warning("Reddit 429: retry in %.1fs (attempt %d/%d)", wait_s, attempt, retries)
                    await asyncio.sleep(wait_s)
                    delay *= 2
                    continue
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            code = e.response.status_code if e.response is not None else "?"
            if 500 <= int(code) < 600 and attempt < retries:
                wait_s = delay + random.random()
                log.warning("Reddit %s: retry in %.1fs (attempt %d/%d)", code, wait_s, attempt, retries)
                await asyncio.sleep(wait_s)
                delay *= 2
                continue
            log.exception("HTTP error from Reddit (attempt %d/%d)", attempt, retries)
            raise
        except Exception:
            if attempt < retries:
                wait_s = delay + random.random()
                log.warning("Reddit request failed: retry in %.1fs (attempt %d/%d)", wait_s, attempt, retries)
                await asyncio.sleep(wait_s)
                delay *= 2
                continue
            log.exception("Reddit request failed (final)")
            raise
    return {}

def _build_query(ticker: str) -> str:
    # Простой и надёжный поиск: сам тикер + сортировка по new, ограничение по времени.
    # Можно расширить на 'title:"TICKER"' при необходимости.
    q = quote_plus(ticker)
    return f"{BASE}?q={q}&sort=new&restrict_sr=0&t={quote_plus(REDDIT_TIME)}&limit={REDDIT_SEARCH_LIMIT}"

async def _search_reddit(ticker: str) -> List[str]:
    url = _build_query(ticker)
    data = await _get_json(url)
    children = data.get("data", {}).get("children", [])
    titles = []
    for it in children:
        d = it.get("data", {})
        title = d.get("title")
        if title:
            titles.append(title)
        if len(titles) >= REDDIT_SEARCH_LIMIT:
            break
    return titles

def _fmt_example(title: str, max_len: int = 80) -> str:
    t = (title or "").replace("\n", " ").strip()
    return (t[: max_len - 1] + "…") if len(t) > max_len else t

async def collect_signals() -> str:
    """
    Возвращает строку формата:
      'GME: 3 упоминаний (напр.: ... ) | RBNE: нет свежих сигналов'
    Ошибки не валят процесс: пишем в лог и возвращаем 'ошибка'.
    """
    try:
        parts: List[str] = []
        for t in TICKERS:
            try:
                posts = await _search_reddit(t)
                if posts:
                    parts.append(f"{t}: {len(posts)} упоминаний (напр.: {_fmt_example(posts[0])})")
                else:
                    parts.append(f"{t}: нет свежих сигналов")
            except Exception:
                log.exception("reddit search failed for %s", t)
                parts.append(f"{t}: ошибка")
        return " | ".join(parts) if parts else "нет тикеров"
    except Exception:
        log.exception("collect_signals failed")
        return "ошибка"
