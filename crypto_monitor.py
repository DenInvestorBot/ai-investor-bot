# crypto_monitor.py
import os
import asyncio
import logging
import random
from typing import List, Dict, Any

import httpx

log = logging.getLogger(__name__)

COINGECKO = os.getenv("COINGECKO_BASE", "https://api.coingecko.com/api/v3")
UA = {"User-Agent": "ai-investor-bot/1.0 (+bot summary)"}
COINS_LIMIT = int(os.getenv("CRYPTO_TREND_LIMIT", "7"))  # Сколько монет показать в краткой сводке


async def _get_json(url: str, *, retries: int = 4) -> Dict[str, Any]:
    """
    Надёжный GET с экспоненциальным бэкоффом.
    Уважает Retry-After при 429, логирует 5xx и не валит процесс.
    """
    delay = 1.0
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(20), headers=UA, http2=True) as client:
                r = await client.get(url)
                # 429: попробуем подождать по Retry-After
                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After")
                    if retry_after:
                        try:
                            wait_s = float(retry_after)
                        except ValueError:
                            wait_s = delay + random.random()
                    else:
                        wait_s = delay + random.random()
                    log.warning("CoinGecko 429 (rate limit). Retry in %.1fs (attempt %d/%d)", wait_s, attempt, retries)
                    await asyncio.sleep(wait_s)
                    delay *= 2
                    continue
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            code = e.response.status_code if e.response is not None else "?"
            if 500 <= int(code) < 600 and attempt < retries:
                wait_s = delay + random.random()
                log.warning("CoinGecko %s. Retry in %.1fs (attempt %d/%d)", code, wait_s, attempt, retries)
                await asyncio.sleep(wait_s)
                delay *= 2
                continue
            log.exception("HTTP error from CoinGecko (attempt %d/%d)", attempt, retries)
            raise
        except Exception:
            if attempt < retries:
                wait_s = delay + random.random()
                log.warning("CoinGecko request failed. Retry in %.1fs (attempt %d/%d)", wait_s, attempt, retries)
                await asyncio.sleep(wait_s)
                delay *= 2
                continue
            log.exception("CoinGecko request failed (final)")
            raise
    return {}  # не должно дойти, но для типизации


def _format_trending(coins: List[Dict[str, Any]]) -> str:
    """
    Форматируем список трендовых монет в короткую строку:
    'Name (SYMBOL, #rank)', до COINS_LIMIT штук.
    """
    items = []
    for c in coins[:COINS_LIMIT]:
        item = c.get("item", {})
        name = item.get("name") or "?"
        sym = item.get("symbol") or "?"
        rank = item.get("market_cap_rank")
        if rank is None:
            items.append(f"{name} ({sym})")
        else:
            items.append(f"{name} ({sym}, #{rank})")
    return ", ".join(items)


async def collect_new_coins() -> str:
    """
    Возвращает краткий список трендовых монет с CoinGecko.
    Это «прокси» для новых/активно запрашиваемых монет — достаточно для ежедневной сводки.
    """
    try:
        data = await _get_json(f"{COINGECKO}/search/trending")
        coins = data.get("coins", [])
        if not coins:
            log.info("CoinGecko: trending empty response")
            return "нет данных"
        return _format_trending(coins)
    except Exception:
        log.exception("collect_new_coins failed")
        return "ошибка"
