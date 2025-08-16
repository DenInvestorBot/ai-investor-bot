import os
import logging
import traceback
import httpx

from signals.advisor import advise, format_advice

log = logging.getLogger(__name__)
print("📄 [advisor_jobs] Модуль загружен")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

def _escape_markdown(text: str) -> str:
    # Отправляем как plain text — экранирование не требуется, но оставим хук
    return text

async def send_to_telegram(text: str) -> None:
    if not TELEGRAM_TOKEN or not ADMIN_CHAT_ID:
        log.warning("send_to_telegram: missing TELEGRAM_BOT_TOKEN or ADMIN_CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": int(ADMIN_CHAT_ID), "text": text}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
    except Exception:
        log.exception("send_to_telegram failed")

async def run_tsla_gme_daily_job():
    """Запуск анализа и рекомендаций для TSLA и GME (асинхронно, без блокировок)"""
    print("🚀 [advisor_jobs] Запуск дневного задания советника (TSLA, GME)")
    tickers = ["TSLA", "GME"]
    for symbol in tickers:
        try:
            rec = advise(symbol, interval="1d", lookback=60)
            if rec:
                message = format_advice(symbol, "1D", rec)
                await send_to_telegram(_escape_markdown(message))
                print(f"✅ [advisor_jobs] Рекомендация по {symbol} отправлена")
            else:
                await send_to_telegram(_escape_markdown(f"Нет данных для {symbol}"))
                print(f"ℹ️ [advisor_jobs] Нет данных для {symbol}")
        except Exception:
            print(f"❌ [advisor_jobs] Ошибка обработки {symbol}:")
            traceback.print_exc()
