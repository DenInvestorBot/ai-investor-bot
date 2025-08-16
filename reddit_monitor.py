# reddit_monitor.py
import os
import asyncio
import logging
import random
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus

import httpx

log = logging.getLogger(__name__)

# ---- ENV ----
DEFAULT_TICKERS = ["GME", "RBNE"]
TICKERS: List[str] = [
    t.strip().upper()
    for t in os.getenv("REDDIT_TICKERS", ",".join(DEFAULT_TICKERS)).split(",")
    if t.strip()
]
REDDIT_TIME = os.getenv("REDDIT_TIME", "day")  # day|week|month|year|all
REDDIT_SEARCH_LIMIT = int(os.getenv("REDDIT_SEARCH_LIMIT", "5"))

# OAuth (userless) — если заданы, используем защищённый эндпоинт
R_CID = os.getenv("REDDIT_CLIENT_ID")
R_SEC = os.getenv("REDDIT_CLIENT_SECRET")
R_UA = os.getenv("REDDIT_USER_AGENT", "ai-investor-bot/1.0 (+reddit signals)")

TIMEOUT = httpx.Timeout(20)

# ---- OAuth helpers ----
_oauth_token: Optional[str] = None
_oauth_expiry: float = 0.0

async def _get_oauth_token() -> Optional[str]:
    """Берём userless токен через client_credentials. Кэшируем до истечения."""
    import time
    global _oauth_token, _oauth_expiry
    if _oauth_token and time.time() < _oauth_expiry - 60:
        return _oauth_token
    if not (R_CID and R_SEC):
        return None
    try:
        auth = (R_CID, R_SEC)
        data = {"grant_type": "client_credentials"}
        headers = {"User-Agent": R_UA}
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers) as client:
            r = await client.post("https://www.reddit.com/api/v1/access_token", auth=auth, data=data)
            r.raise_for_status()
            js = r.json()
            _oauth_token = js.get("access_token")
            _oauth_expiry = time.time() + int(js.get("expires_in", 3600))
            return _oauth_token
    except Exception:
        log.exception("Reddit OAuth: не удалось получить токен")
        return None

# ---- HTTP utils ----
async def _get_json(url: str, headers: Dict[str, str], *, retries: int = 3) -> Dict[str, Any]:
    delay = 1.0
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers, http2=True) as client:
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
            if isinstance(code, int) and 500 <= code < 600 and attempt < retries:
                wait_s = delay + random.random()
                log.warning("Reddit %s: retry in %.1fs (attempt %d/%d)", code, wait_s, attempt, retries)
                await asyncio.sleep(wait_s)
                delay *= 2
                continue
            log.exception("HTTP error from Reddit (attempt %d/%d)", attempt, retries)
            break
        except Exception:
            if attempt < retries:
                wait_s = delay + random.random()
                log.warning("Reddit request failed: retry in %.1fs (attempt %d/%d)", wait_s, attempt, retries)
                await asyncio.sleep(wait_s)
                delay *= 2
                continue
            log.exception("Reddit request failed (final)")
            break
    return {}

def _fmt_example(title: str, max_len: int = 80) -> str:
    t = (title or "").replace("\n", " ").strip()
    return (t[: max_len - 1] + "…") if len(t) > max_len else t

# ---- Search (OAuth first, then public) ----
async def _search_reddit_oauth(ticker: str) -> List[str]:
    token = await _get_oauth_token()
    if not token:
        return []
    q = quote_plus(ticker)
    url = f"https://oauth.reddit.com/search?q={q}&sort=new&t={quote_plus(REDDIT_TIME)}&limit={REDDIT_SEARCH_LIMIT}"
    headers = {"Authorization": f"Bearer {token}", "User-Agent": R_UA}
    data = await _get_json(url, headers)
    children = data.get("data", {}).get("children", [])
    return [it.get("data", {}).get("title") for it in children if it.get("data", {}).get("title")][:REDDIT_SEARCH_LIMIT]

async def _search_reddit_public(ticker: str) -> List[str]:
    q = quote_plus(ticker)
    url = f"https://www.reddit.com/search.json?q={q}&sort=new&restrict_sr=0&t={quote_plus(REDDIT_TIME)}&limit={REDDIT_SEARCH_LIMIT}"
    headers = {"User-Agent": R_UA}
    data = await _get_json(url, headers)
    children = data.get("data", {}).get("children", [])
    return [it.get("data", {}).get("title") for it in children if it.get("data", {}).get("title")][:REDDIT_SEARCH_LIMIT]

async def _search_reddit(ticker: str) -> List[str]:
    # Пробуем OAuth, если есть ключи; иначе — публичный
    if R_CID and R_SEC:
        titles = await _search_reddit_oauth(ticker)
        if titles:
            return titles
        # если OAuth не дал — fallback на public
    return await _search_reddit_public(ticker)

# ---- Public API ----
async def collect_signals() -> str:
    """
    'GME: 3 упоминаний (напр.: ...) | RBNE: нет свежих сигналов'
    Любые сбои => "нет свежих сигналов" (причина в логах).
    """
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
            parts.append(f"{t}: нет свежих сигналов")
    return " | ".join(parts) if parts else "нет тикеров"
