# reddit_monitor.py
import os
import asyncio
import logging
import random
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import quote_plus
from collections import Counter

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

# Настройка краткого анализа
USE_LLM = (os.getenv("REDDIT_SUMMARY_LLM", "1") not in ("0", "false", "False")) and bool(os.getenv("OPENAI_API_KEY"))
LLM_MODEL = os.getenv("REDDIT_SUMMARY_MODEL", "gpt-4o-mini")
LLM_MAXTOK = int(os.getenv("REDDIT_SUMMARY_MAXTOK", "120"))
SUMMARY_CHARS = int(os.getenv("REDDIT_SUMMARY_CHARS", "180"))  # итоговая длина строки

# OAuth (userless) — если заданы, используем защищённый эндпоинт
R_CID = os.getenv("REDDIT_CLIENT_ID")
R_SEC = os.getenv("REDDIT_CLIENT_SECRET")
R_UA = os.getenv("REDDIT_USER_AGENT", "ai-investor-bot/1.0 (+reddit signals)")

TIMEOUT = httpx.Timeout(20)

# ---- OAuth helpers ----
_oauth_token: Optional[str] = None
_oauth_expiry: float = 0.0

async def _get_oauth_token() -> Optional[str]:
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

# ---- Search (OAuth first, then public) ----
def _extract_titles_texts(data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    children = data.get("data", {}).get("children", [])
    titles, texts = [], []
    for it in children:
        d = it.get("data", {}) or {}
        t = d.get("title")
        if t:
            titles.append(t)
        selftext = d.get("selftext") or ""
        if selftext and len(texts) < REDDIT_SEARCH_LIMIT:
            texts.append(selftext[:400])
        if len(titles) >= REDDIT_SEARCH_LIMIT:
            break
    return titles, texts

async def _search_reddit_oauth(ticker: str) -> Tuple[List[str], List[str]]:
    token = await _get_oauth_token()
    if not token:
        return [], []
    q = quote_plus(ticker)
    url = f"https://oauth.reddit.com/search?q={q}&sort=new&t={quote_plus(REDDIT_TIME)}&limit={REDDIT_SEARCH_LIMIT}"
    headers = {"Authorization": f"Bearer {token}", "User-Agent": R_UA}
    data = await _get_json(url, headers)
    return _extract_titles_texts(data)

async def _search_reddit_public(ticker: str) -> Tuple[List[str], List[str]]:
    q = quote_plus(ticker)
    url = f"https://www.reddit.com/search.json?q={q}&sort=new&restrict_sr=0&t={quote_plus(REDDIT_TIME)}&limit={REDDIT_SEARCH_LIMIT}"
    headers = {"User-Agent": R_UA}
    data = await _get_json(url, headers)
    return _extract_titles_texts(data)

async def _search_reddit(ticker: str) -> Tuple[List[str], List[str]]:
    if R_CID and R_SEC:
        titles, texts = await _search_reddit_oauth(ticker)
        if titles:
            return titles, texts
    return await _search_reddit_public(ticker)

# ---- Local summarizer (fallback) ----
_STOP = {
    # en
    "the","a","an","of","to","in","on","and","or","for","with","without","by","from","at","is","are","was","were",
    "it","this","that","as","be","has","have","had","will","about","over","under","into","out","up","down","vs","&",
    # ru
    "и","в","во","на","с","со","у","к","от","за","до","по","из","для","без","над","под","о","об","как","что","это",
    "а","но","же","ли","или","уже","бы","не","ни","да","то","там","тут","только","еще","есть","были","будет",
}
_POS_WORDS = {"buy","long","bull","call","squeeze","moon","green","breakout","рост","покупать","бычий","пробой"}
_NEG_WORDS = {"sell","short","put","dump","red","bear","down","collapse","слив","шорт","медв","паден","продавать"}
_TOKEN_RE = re.compile(r"[A-Za-zА-Яа-я0-9$%+#@\-']+")

def _tokens(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]

def _top_phrases(texts: List[str], top_n: int = 3) -> List[str]:
    words = [w for t in texts for w in _tokens(t) if w not in _STOP and len(w) > 2]
    if not words:
        return []
    bigr = Counter([" ".join(pair) for pair in zip(words, words[1:])])
    trgr = Counter([" ".join(tri) for tri in zip(words, words[1:], words[2:])])
    mix = (trgr + Counter())
    for k, v in bigr.items():
        mix[k] += int(v * 0.6)
    phrases = [p for p, _ in mix.most_common(5) if not any(ch.isdigit() for ch in p)]
    return phrases[:top_n]

def _sentiment_hint(texts: List[str]) -> Optional[str]:
    w = [t.lower() for t in _TOKEN_RE.findall(" ".join(texts))]
    pos = sum(any(p in token for p in _POS_WORDS) for token in w)
    neg = sum(any(n in token for n in _NEG_WORDS) for token in w)
    if pos == 0 and neg == 0:
        return None
    if pos > neg * 1.2:
        return "тон скорее позитивный"
    if neg > pos * 1.2:
        return "тон скорее негативный"
    return "тон нейтральный/смешанный"

def _local_summary(titles: List[str], texts: List[str]) -> str:
    if not titles:
        return "нет свежих сигналов"
    bucket = titles + [t[:240] for t in texts]
    phrases = _top_phrases(bucket, top_n=3)
    senti = _sentiment_hint(bucket)
    parts: List[str] = []
    if phrases:
        parts.append("ключевые темы: " + ", ".join(phrases))
    if senti:
        parts.append(senti)
    s = " · ".join(parts) if parts else (titles[0][:79] + "…") if len(titles[0]) > 80 else titles[0]
    return s[:SUMMARY_CHARS]

# ---- LLM summarizer (optional) ----
async def _llm_summary(ticker: str, titles: List[str], texts: List[str]) -> Optional[str]:
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI()
        # готовим компактный контент
        joined = "\n".join(["• " + t for t in titles[:REDDIT_SEARCH_LIMIT]])
        if texts:
            joined += "\n\nФрагменты постов:\n" + "\n".join(["— " + x[:200] for x in texts[:REDDIT_SEARCH_LIMIT]])
        system = (
            "Ты финтех-ассистент. На основе заголовков и коротких фрагментов "
            f"про тикер {ticker} дай ОДНО предложение по-русски (≤ {SUMMARY_CHARS} символов): что обсуждают и общий тон."
            " Без эмодзи, без ссылок, без домыслов. Если данных мало — скажи 'нет свежих сигналов'."
        )
        resp = await client.responses.create(
            model=LLM_MODEL,
            max_output_tokens=LLM_MAXTOK,
            temperature=0.3,
            input=[{"role": "system", "content": system},
                   {"role": "user", "content": joined}]
        )
        text = resp.output_text.strip()
        return text[:SUMMARY_CHARS] if text else None
    except Exception:
        log.exception("LLM summary failed")
        return None

# ---- Public API ----
async def collect_signals() -> str:
    """
    Пример:
      'GME: 5 упоминаний — ключевые темы: ... · тон скорее ... | RBNE: нет свежих сигналов'
    Если есть OPENAI_API_KEY и REDDIT_SUMMARY_LLM!=0 — используем LLM, иначе — локальный разбор.
    Любые ошибки не валят процесс.
    """
    parts: List[str] = []
    for t in TICKERS:
        try:
            titles, texts = await _search_reddit(t)
            if not titles:
                parts.append(f"{t}: нет свежих сигналов")
                continue
            brief: Optional[str] = None
            if USE_LLM:
                brief = await _llm_summary(t, titles, texts)
            if not brief:
                brief = _local_summary(titles, texts)
            parts.append(f"{t}: {len(titles)} упоминаний — {brief}")
        except Exception:
            log.exception("reddit search failed for %s", t)
            parts.append(f"{t}: нет свежих сигналов")
    return " | ".join(parts) if parts else "нет тикеров"
