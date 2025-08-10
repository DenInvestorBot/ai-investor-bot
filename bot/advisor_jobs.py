# bot/advisor_jobs.py
from __future__ import annotations
import os, sqlite3
from typing import Iterable
import pandas as pd

from data.stocks import load_stock_ohlcv_daily
from signals.advisor import advise, format_advice

STATE_DB = os.getenv("ADVISOR_STATE_DB", "advisor_state.sqlite")
TIMEFRAME = "1D"
SYMBOLS = ["TSLA", "GME"]

# --- State (prevent duplicate sends for same trading day) ---
def _db():
    conn = sqlite3.connect(STATE_DB, isolation_level=None, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS advice_sent (
        symbol TEXT,
        candle_date TEXT,
        PRIMARY KEY(symbol, candle_date)
    )
    """)
    return conn

def _already_sent(conn, symbol: str, date_str: str) -> bool:
    cur = conn.execute("SELECT 1 FROM advice_sent WHERE symbol=? AND candle_date=?", (symbol, date_str))
    return cur.fetchone() is not None

def _mark_sent(conn, symbol: str, date_str: str):
    conn.execute("INSERT OR IGNORE INTO advice_sent(symbol,candle_date) VALUES(?,?)", (symbol, date_str))

# --- Core ---
def send_advice_for(symbol: str):
    df = load_stock_ohlcv_daily(symbol)
    if len(df) < 220:
        return  # not enough data
    last_ts = df.index[-1]
    date_str = pd.Timestamp(last_ts).strftime("%Y-%m-%d")

    conn = _db()
    if _already_sent(conn, symbol, date_str):
        return

    rec = advise(df, use_volume=True, sl_atr_mult=1.5, rr=3.0)
    msg = format_advice(symbol, TIMEFRAME, rec, candle_time=last_ts)

    # Try your bot's notifier first
    try:
        from bot.notify import send_text
        send_text(msg)
    except Exception:
        print(msg)

    _mark_sent(conn, symbol, date_str)

def run_tsla_gme_daily_job(symbols: Iterable[str] = None):
    for s in (symbols or SYMBOLS):
        try:
            send_advice_for(s)
        except Exception as e:
            try:
                from bot.notify import send_text
                send_text(f"⚠️ Advisor error for {s}: {e}")
            except Exception:
                print("advisor error:", s, e)
