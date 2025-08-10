from signals.advisor import advise, format_advice
from telegram import Bot
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_TOKEN)

def run_tsla_gme_daily_job():
    tickers = ["TSLA", "GME"]
    for symbol in tickers:
        rec = advise(symbol, interval="1d", lookback=60)
        if rec:
            message = format_advice(symbol, "1D", rec)
            bot.send_message(chat_id=CHAT_ID, text=message)
        else:
            bot.send_message(chat_id=CHAT_ID, text=f"Net dannyh dlya {symbol}")
