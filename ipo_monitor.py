# ipo_monitor.py
import os
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from zoneinfo import ZoneInfo

import httpx

log = logging.getLogger(__name__)

TZ = ZoneInfo(os.getenv("TZ", "Europe/Riga"))
IPO_LOOKAHEAD_DAYS = int(os.getenv("IPO_LOOKAHEAD_DAYS", "14"))
IPO_LIMIT = int(os.getenv("IPO_LIMIT", "5"))
PROVIDER = os.getenv("IPO_PROVIDER", "").lower().strip()
FMP_KEY = os.getenv("FMP_API_KEY") or os.getenv("IPO_API_KEY")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")

UA = {"User-Agent": "ai-investor-bot/1.0 (+ipo monitor)"}
TIMEOUT = httpx.Timeout(25.0)

def _date_range() -> (str, str):
    now = datetime.now(tz=TZ).date()
    return now.isoformat(), (now + timedelta(days=IPO_LOOKAHEAD_DAYS)).isoformat()

async def _get_json(url: str, *, headers: Optional[Dict[str, str]] = None, retries: int = 4) -> Dict[str, Any]:
    delay = 1.0
    headers = {**UA, **(headers or {})}
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
                    log.warning("IPO 429: retry in %.1fs (attempt %d/%d)", wait_s, attempt, retries)
                    await asyncio.sleep(wait_s)
                    delay *= 2
                    continue
                r.raise_for_status()
                return r.json()
        except Exception:
            if attempt < retries:
                wait_s = delay + random.random()
                log.warning("IPO request failed. Retry in %.1fs (attempt %d/%d)", wait_s, attempt, retries)
                await asyncio.sleep(wait_s)
                delay *= 2
                continue
            log.exception("IPO request failed (final)")
            break
    return {}

async def _fetch_fmp(fr: str, to: str) -> List[Dict[str, Any]]:
    if not FMP_KEY:
        return []
    data = await _get_json(f"https://financialmodelingprep.com/api/v3/ipo_calendar?from={fr}&to={to}&apikey={FMP_KEY}")
    if isinstance(data, dict):
        data = data.get("ipoCalendar") or data.get("data") or []
    return data or []

async def _fetch_finnhub(fr: str, to: str) -> List[Dict[str, Any]]:
    if not FINNHUB_KEY:
        return []
    data = await _get_json(f"https://finnhub.io/api/v1/calendar/ipo?from={fr}&to={to}&token={FINNHUB_KEY}")
    return data.get("ipoCalendar", []) if isinstance(data, dict) else []

def _fmt_item(d: Dict[str, Any]) -> str:
    date = d.get("date") or d.get("priced")
    try:
        if isinstance(date, (int, float)):
            date = datetime.fromtimestamp(date, tz=TZ).date().isoformat()
    except Exception:
        pass
    date = str(date) if date else "?"
    symbol = d.get("symbol") or d.get("ticker") or "?"
    name = d.get("company") or d.get("companyName") or d.get("name") or "?"
    price = d.get("priceRange") or d.get("price") or None
    if not price and d.get("priceLow") and d.get("priceHigh"):
        price = f"${d.get('priceLow')}–${d.get('priceHigh')}"
    if isinstance(price, str) and price and not price.startswith("$"):
        price = f"${price}"
    return f"{date} {symbol} {name} ({price})" if price else f"{date} {symbol} {name}"

def _format_list(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "нет новых IPO"
    try:
        items = sorted(items, key=lambda d: datetime.fromisoformat(str(d.get("date"))))
    except Exception:
        pass
    top = items[:IPO_LIMIT]
    rest = max(0, len(items) - len(top))
    s = " | ".join(_fmt_item(x) for x in top)
    if rest:
        s += f" | +{rest} ещё"
    return s

async def collect_ipos() -> str:
    """Любые сбои → 'нет новых IPO' (причина в логах)"""
    try:
        fr, to = _date_range()
        items: List[Dict[str, Any]] = []
        if PROVIDER == "fmp" and FMP_KEY:
            items = await _fetch_fmp(fr, to)
        elif PROVIDER == "finnhub" and FINNHUB_KEY:
            items = await _fetch_finnhub(fr, to)
        else:
            if FMP_KEY:
                items = await _fetch_fmp(fr, to)
            elif FINNHUB_KEY:
                items = await _fetch_finnhub(fr, to)
        return _format_list(items)
    except Exception:
        log.exception("collect_ipos failed")
        return "нет новых IPO"
