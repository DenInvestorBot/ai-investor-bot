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
IPO_LOOKAHEAD_DAYS = int(os.getenv("IPO_LOOKAHEAD_DAYS", "14"))      # горизонт вперёд
IPO_LIMIT = int(os.getenv("IPO_LIMIT", "5"))                          # сколько элементов печатать
PROVIDER = os.getenv("IPO_PROVIDER", "").lower().strip()              # 'fmp' | 'finnhub' | ''
FMP_KEY = os.getenv("FMP_API_KEY")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")

UA = {"User-Agent": "ai-investor-bot/1.0 (+ipo monitor)"}
TIMEOUT = httpx.Timeout(25.0)


# ---- Вспомогательные функции ----
def _date_range() -> (str, str):
    now = datetime.now(tz=TZ).date()
    start = now
    end = now + timedelta(days=IPO_LOOKAHEAD_DAYS)
    return start.isoformat(), end.isoformat()

async def _get_json(url: str, *, headers: Optional[Dict[str, str]] = None, retries: int = 4) -> Dict[str, Any]:
    """
    Надёжный GET с экспоненциальным бэкоффом и уважением Retry-After на 429.
    """
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


# ---- Провайдеры ----
async def _fetch_fmp(from_date: str, to_date: str) -> List[Dict[str, Any]]:
    """
    FinancialModelingPrep IPO Calendar:
      GET https://financialmodelingprep.com/api/v3/ipo_calendar?from=YYYY-MM-DD&to=YYYY-MM-DD&apikey=...
    Ответ обычно: [{"date":"2025-08-19","symbol":"ABCD","company":"Acme, Inc.","priceRange":"$18.00 - $20.00", ...}, ...]
    """
    if not FMP_KEY:
        return []
    url = f"https://financialmodelingprep.com/api/v3/ipo_calendar?from={from_date}&to={to_date}&apikey={FMP_KEY}"
    data = await _get_json(url)
    if isinstance(data, dict):
        # на всякий случай ключ data
        data = data.get("ipoCalendar") or data.get("data") or []
    return data or []

async def _fetch_finnhub(from_date: str, to_date: str) -> List[Dict[str, Any]]:
    """
    Finnhub IPO Calendar:
      GET https://finnhub.io/api/v1/calendar/ipo?from=YYYY-MM-DD&to=YYYY-MM-DD&token=...
    Ответ: {"ipoCalendar":[{"date":"2025-08-19","symbol":"ABCD","name":"Acme, Inc.","price":"18-20", ...}, ...]}
    """
    if not FINNHUB_KEY:
        return []
    url = f"https://finnhub.io/api/v1/calendar/ipo?from={from_date}&to={to_date}&token={FINNHUB_KEY}"
    data = await _get_json(url)
    return data.get("ipoCalendar", []) if isinstance(data, dict) else []


def _fmt_price(*vals: Optional[str]) -> Optional[str]:
    for v in vals:
        if v and isinstance(v, str) and v.strip() and v.strip() != "0":
            s = v.strip().lstrip("$")
            return f"${s}"
    return None

def _fmt_item(d: Dict[str, Any]) -> str:
    """
    Нормализуем разные структуры провайдеров в одну строку:
      '2025-08-19 ABCD Acme Inc. ($18–20)'
    """
    # Дата
    date = d.get("date") or d.get("priced")
    if isinstance(date, (int, float)):
        try:
            date = datetime.fromtimestamp(date, tz=TZ).date().isoformat()
        except Exception:
            date = str(date)
    date = str(date) if date else "?"

    # Тикер / название
    symbol = d.get("symbol") or d.get("ticker") or d.get("s") or "?"
    name = d.get("company") or d.get("companyName") or d.get("name") or d.get("n") or "?"

    # Цена / диапазон
    price_range = d.get("priceRange") or d.get("price") or d.get("priceLow") or d.get("priceHigh")
    price = None
    if isinstance(price_range, (str,)):
        # "18-20" или "$18.00 - $20.00"
        price = price_range.replace(" - ", "–").replace("-", "–").replace("$", "").strip()
        if price:
            price = f"${price}"
    elif isinstance(price_range, (int, float)):
        price = f"${price_range}"
    else:
        # Попробуем собрать из low/high
        low = d.get("priceLow")
        high = d.get("priceHigh")
        if low and high:
            price = _fmt_price(f"{low}–{high}", str(low), str(high))
        else:
            price = _fmt_price(str(d.get("price")), str(d.get("priceRange")))

    if price:
        return f"{date} {symbol} {name} ({price})"
    return f"{date} {symbol} {name}"

def _format_list(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "нет новых IPO"
    # Сортируем по дате, если возможно
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


# ---- Публичная функция ----
async def collect_ipos() -> str:
    """
    Возвращает строку с ближайшими IPO в горизонте IPO_LOOKAHEAD_DAYS.
    Провайдеры: FMP (FMP_API_KEY), Finnhub (FINNHUB_API_KEY). Если ключей нет — 'нет новых IPO'.
    Ошибки не валят процесс.
    """
    try:
        start, end = _date_range()

        items: List[Dict[str, Any]] = []
        # Приоритет явного выбора провайдера
        if PROVIDER == "fmp" and FMP_KEY:
            items = await _fetch_fmp(start, end)
        elif PROVIDER == "finnhub" and FINNHUB_KEY:
            items = await _fetch_finnhub(start, end)
        else:
            # Автовыбор: FMP > Finnhub по наличию ключей
            if FMP_KEY:
                items = await _fetch_fmp(start, end)
            elif FINNHUB_KEY:
                items = await _fetch_finnhub(start, end)

        if not items:
            # Нет ключей или пустой ответ — корректно сообщаем
            if not (FMP_KEY or FINNHUB_KEY):
                log.warning("collect_ipos: no provider keys set (FMP_API_KEY / FINNHUB_API_KEY)")
            return "нет новых IPO"

        return _format_list(items)
    except Exception:
        log.exception("collect_ipos failed")
        return "ошибка"
