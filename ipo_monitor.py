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

# ---- Настройки (ENV) ----
TZ = ZoneInfo(os.getenv("TZ", "Europe/Riga"))
IPO_LOOKAHEAD_DAYS = int(os.getenv("IPO_LOOKAHEAD_DAYS", "14"))
IPO_LIMIT = int(os.getenv("IPO_LIMIT", "5"))
PROVIDER = os.getenv("IPO_PROVIDER", "").lower().strip()  # 'fmp' | 'finnhub' | ''
# поддерживаем старое имя ключа:
FMP_KEY = os.getenv("FMP_API_KEY") or os.getenv("IPO_API_KEY")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")

UA = {"User-Agent": "ai-investor-bot/1.0 (+ipo monitor)"}
TIMEOUT = httpx.Timeout(25.0)

def _date_range() -> (str, str):
    now = datetime.now(tz=TZ).date()
    start = now
    end = now + timedelta(days=IPO_LOOKAHEAD_DAYS)
    return start.isoformat(), end.isoformat()

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
        except httpx.HTTPStatusError as e:
            code = e.response.status_code if e.response is not None else "?"
            if isinstance(code, int) and 500 <= code < 600 and attempt < retries:
                wait_s = delay + random.random()
                log.warning("IPO %s: retry in %.1fs (attempt %d/%d)", code, wait_s, attempt, retries)
                await asyncio.sleep(wait_s)
                delay *= 2
                continue
            log.exception("HTTP error during IPO fetch (attempt %d/%d)", attempt, retries)
            raise
        except Exception:
            if attempt < retries:
                wait_s = delay + random.random()
                log.warning("IPO request failed: retry in %.1fs (attempt %d/%d)", wait_s, attempt, retries)
                await asyncio.sleep(wait_s)
                delay *= 2
                continue
            log.exception("IPO request failed (final)")
            raise
    return {}

async def _fetch_fmp(from_date: str, to_date: str) -> List[Dict[str, Any]]:
    if not FMP_KEY:
        return []
    url = f"https://financialmodelingprep.com/api/v3/ipo_calendar?from={from_date}&to={to_date}&apikey={FMP_KEY}"
    data = await _get_json(url)
    if isinstance(data, dict):
        data = data.get("ipoCalendar") or data.get("data") or []
    return data or []

async def _fetch_finnhub(from_date: str, to_date: str) -> List[Dict[str, Any]]:
    if not FINNHUB_KEY:
        return []
    url = f"https://finnhub.io/api/v1/calendar/ipo?from={from_date}&to={to_date}&token={FINNHUB_KEY}"
    data = await _get_json(url)
    return data.get("ipoCalendar", []) if isinstance(data, dict) else []

def _fmt_price(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    s = str(val).strip().lstrip("$")
    return f"${s}" if s else None

def _fmt_item(d: Dict[str, Any]) -> str:
    date = d.get("date") or d.get("priced")
    if isinstance(date, (int, float)):
        try:
            date = datetime.fromtimestamp(date, tz=TZ).date().isoformat()
        except Exception:
            date = str(date)
    date = str(date) if date else "?"
    symbol = d.get("symbol") or d.get("ticker") or d.get("s") or "?"
    name = d.get("company") or d.get("companyName") or d.get("name") or d.get("n") or "?"
    price = (
        _fmt_price(d.get("priceRange"))
        or _fmt_price(d.get("price"))
        or (f"${d.get('priceLow')}–${d.get('priceHigh')}" if d.get("priceLow") and d.get("priceHigh") else None)
    )
    return f"{date} {symbol} {name} ({price})" if price else f"{date} {symbol} {name}"

def _format_list(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "нет новых IPO"
    def _key(d):
        try:
            return datetime.fromisoformat(str(d.get("date")))
        except Exception:
            return datetime.max
    items_sorted = sorted(items, key=_key)
    top = items_sorted[:IPO_LIMIT]
    rest = max(0, len(items_sorted) - len(top))
    s = " | ".join(_fmt_item(x) for x in top)
    if rest:
        s += f" | +{rest} ещё"
    return s

async def collect_ipos() -> str:
    try:
        start, end = _date_range()
        items: List[Dict[str, Any]] = []
        if PROVIDER == "fmp" and FMP_KEY:
            items = await _fetch_fmp(start, end)
        elif PROVIDER == "finnhub" and FINNHUB_KEY:
            items = await _fetch_finnhub(start, end)
        else:
            if FMP_KEY:
                items = await _fetch_fmp(start, end)
            elif FINNHUB_KEY:
                items = await _fetch_finnhub(start, end)

        if not items:
            if not (FMP_KEY or FINNHUB_KEY):
                log.warning("collect_ipos: no provider keys set (FMP_API_KEY/IPO_API_KEY or FINNHUB_API_KEY)")
            return "нет новых IPO"
        return _format_list(items)
    except Exception:
        log.exception("collect_ipos failed")
        return "ошибка"
