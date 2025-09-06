# crypto_monitor.py — sync версия на requests
import os
import time
import logging
import random
from typing import List, Dict, Any

import requests

log = logging.getLogger(__name__)

COINGECKO = os.getenv("COINGECKO_BASE", "https://api.coingecko.com/api/v3")
UA = {"User-Agent": "ai-investor-bot/1.0 (+bot summary)"}
COINS_LIMIT = int(os.getenv("CRYPTO_TREND_LIMIT", "7"))  # сколько монет показать в краткой сводке

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CRYPTO_TREND_ALERTS = os.getenv("CRYPTO_TREND_ALERTS", "1") not in ("0", "false", "False")


def _get_json(url: str, *, retries: int = 4, timeout: int = 20) -> Dict[str, Any]:
    """Надёжный GET с экспоненциальным бэкоффом и учётом 429/5xx."""
    delay = 1.0
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait_s = float(retry_after)
                    except ValueError:
                        wait_s = delay + random.random()
                else:
                    wait_s = delay + random.random()
                log.warning("CoinGecko 429. Retry in %.1fs (attempt %d/%d)", wait_s, attempt, retries)
                time.sleep(wait_s); delay *= 2; continue
            if 500 <= r.status_code < 600 and attempt < retries:
                wait_s = delay + random.random()
                log.warning("CoinGecko %s. Retry in %.1fs (attempt %d/%d)", r.status_code, wait_s, attempt, retries)
                time.sleep(wait_s); delay *= 2; continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt < retries:
                wait_s = delay + random.random()
                log.warning("CoinGecko request failed. Retry in %.1fs (attempt %d/%d)", wait_s, attempt, retries)
                time.sleep(wait_s); delay *= 2; continue
            log.exception("CoinGecko request failed (final)")
            raise
    return {}


def _format_trending(coins: List[Dict[str, Any]]) -> str:
    """Формат: 'Name (SYMBOL, #rank)', до COINS_LIMIT штук."""
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


def collect_new_coins() -> str:
    """Краткая сводка трендовых монет CoinGecko."""
    try:
        data = _get_json(f"{COINGECKO}/search/trending")
        coins = data.get("coins", [])
        if not coins:
            log.info("CoinGecko: trending empty response")
            return "нет данных"
        return _format_trending(coins)
    except Exception:
        log.exception("collect_new_coins failed")
        return "ошибка"


def _send_telegram(text: str) -> None:
    """Отправка в Telegram Bot API (без python-telegram-bot)."""
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        log.info("TELEGRAM_BOT_TOKEN/CHAT_ID не заданы — пропускаю отправку")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
    except requests.RequestException:
        log.exception("Не удалось отправить сообщение в Telegram")


def run_crypto_monitor() -> None:
    """Синхронная точка входа для планировщика."""
    summary = collect_new_coins()
    msg = f"🟢 Трендовые монеты CoinGecko: {summary}"
    log.info(msg)
    if CRYPTO_TREND_ALERTS:
        _send_telegram(msg)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_crypto_monitor()
