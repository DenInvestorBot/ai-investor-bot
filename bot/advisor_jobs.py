import os
from signals.advisor import advise, format_advice
from telegram import Bot
import traceback

print("📄 [advisor_jobs] Модуль загружен")

# ===== Настройка переменных окружения =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID", "0"))

if not TELEGRAM_TOKEN or CHAT_ID == 0:
    print("⚠️ [advisor_jobs] ВНИМАНИЕ: Не заданы TELEGRAM_TOKEN и/или CHAT_ID — уведомления советника не будут отправляться")

bot = None
if TELEGRAM_TOKEN and CHAT_ID:
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
    except Exception:
        print("❌ [advisor_jobs] Ошибка инициализации Telegram-бота:")
        traceback.print_exc()

def run_tsla_gme_daily_job():
    """Запуск анализа и рекомендаций для TSLA и GME"""
    print("🚀 [advisor_jobs] Запуск дневного задания советника (TSLA, GME)")

    if not bot:
        print("⚠️ [advisor_jobs] Telegram-бот не инициализирован — пропуск отправки")
        return

    tickers = ["TSLA", "GME"]
    for symbol in tickers:
        try:
            rec = advise(symbol, interval="1d", lookback=60)
            if rec:
                message = format_advice(symbol, "1D", rec)
                bot.send_message(chat_id=CHAT_ID, text=message)
                print(f"✅ [advisor_jobs] Рекомендация по {symbol} отправлена")
            else:
                bot.send_message(chat_id=CHAT_ID, text=f"Нет данных для {symbol}")
                print(f"ℹ️ [advisor_jobs] Нет данных для {symbol}")
        except Exception:
            print(f"❌ [advisor_jobs] Ошибка обработки {symbol}:")
            traceback.print_exc()
