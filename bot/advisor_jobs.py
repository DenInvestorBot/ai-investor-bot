import os
import traceback
from signals.advisor import advise, format_advice
from crypto_monitor import send_to_telegram, _escape_markdown

print("📄 [advisor_jobs] Модуль загружен")

def run_tsla_gme_daily_job():
    """Запуск анализа и рекомендаций для TSLA и GME"""
    print("🚀 [advisor_jobs] Запуск дневного задания советника (TSLA, GME)")

    tickers = ["TSLA", "GME"]
    for symbol in tickers:
        try:
            rec = advise(symbol, interval="1d", lookback=60)
            if rec:
                message = format_advice(symbol, "1D", rec)
                send_to_telegram(_escape_markdown(message))
                print(f"✅ [advisor_jobs] Рекомендация по {symbol} отправлена")
            else:
                send_to_telegram(_escape_markdown(f"Нет данных для {symbol}"))
                print(f"ℹ️ [advisor_jobs] Нет данных для {symbol}")
        except Exception:
            print(f"❌ [advisor_jobs] Ошибка обработки {symbol}:")
            traceback.print_exc()
