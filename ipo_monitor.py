# ipo_monitor.py — requests-only
import os
import logging
import time
import random
from typing import List, Dict, Any
import requests

log = logging.getLogger(__name__)

# Можно указать свой JSON-эндпоинт с IPO (или прокси сервер), например:
# {"items":[{"symbol":"ABC","company":"Acme Corp","date":"2025-09-10","price":"$12-14"}]}
IPO_FEED_URL = os.getenv("IPO_FEED_URL", "").strip()

def _send_telegram(text: str) -> None:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or
             os.getenv("BOT_TOKEN") or
             os.getenv("TG_BOT_TOKEN"))
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or
               os.getenv("CHAT_ID") or
               os.getenv("TG_CHAT_ID"))
    if not (token and chat_id):
        log.info("IPO: TG token/chat_id не заданы — пропускаю отправку")
        return
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
                          timeout=15)
        r.raise_for_status()
    except requests.RequestException:
        log.exception("IPO: не удалось отправить сообщение в Telegram")

def _get_json(url: str, retries: int = 3, timeout: int = 20) -> Dict[str, Any]:
    delay = 1.0
    for attempt in range(1, retries+1):
        try:
            r = requests.get(url, headers={"User-Agent": "ai-investor-bot/ipo/1.0"}, timeout=timeout)
            if r.status_code == 429 and attempt < retries:
                wait = float(r.headers.get("Retry-After") or delay + random.random())
                log.warning("IPO feed 429. Retry in %.1fs", wait); time.sleep(wait); delay *= 2; continue
            if 500 <= r.status_code < 600 and attempt < retries:
                wait = delay + random.random()
                log.warning("IPO feed %s. Retry in %.1fs", r.status_code, wait); time.sleep(wait); delay *= 2; continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt < retries:
                wait = delay + random.random()
                log.warning("IPO feed request failed. Retry in %.1fs", wait); time.sleep(wait); delay *= 2; continue
            log.exception("IPO feed request failed (final)")
            return {}
    return {}

def _format_items(items: List[Dict[str, Any]]) -> str:
    lines = []
    for it in items[:10]:
        sym = it.get("symbol") or "?"
        name = it.get("company") or it.get("name") or "Company"
        date = it.get("date") or it.get("pricingDate") or "?"
        price = it.get("price") or it.get("priceRange") or ""
        line = f"• <b>{sym}</b> — {name} | {date}"
        if price:
            line += f" | {price}"
        lines.append(line)
    return "\n".join(lines) if lines else "пусто"

def run_ipo_monitor():
    """Тянет список IPO из произвольного JSON-фида (если задан), логирует и шлёт краткую сводку."""
    if not IPO_FEED_URL:
        log.info("IPO: не задан IPO_FEED_URL — задача пропущена (ok)")
        return

    data = _get_json(IPO_FEED_URL)
    items = data.get("items") or data.get("ipos") or data.get("results") or []
    if not isinstance(items, list):
        log.warning("IPO: неожиданный формат ответа (нет списка items)")
        return

    text = "🗓️ Предстоящие/свежие IPO:\n" + _format_items(items)
    log.info(text.replace("\n", " | "))
    _send_telegram(text)

# Совместимость с авто-детектом
def run():
    run_ipo_monitor()

def main():
    run_ipo_monitor()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_ipo_monitor()
