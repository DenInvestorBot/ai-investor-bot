# data/stocks.py
# Simple daily OHLCV loader for US stocks via yfinance
from __future__ import annotations
import pandas as pd
import yfinance as yf
import traceback

print("📄 [data/stocks] Модуль загружен")

__all__ = ["load_stock_ohlcv_daily"]

def load_stock_ohlcv_daily(symbol: str, lookback_days: int = 430) -> pd.DataFrame:
    """
    Возвращает DataFrame с колонками [open, high, low, close, volume], индекс UTC.
    Использует Yahoo Finance daily data. Только закрытые дневные свечи.
    """
    try:
        print(f"🚀 [stocks] Загрузка данных для {symbol} ({lookback_days} дней)")
        df = yf.download(
            tickers=symbol,
            period=f"{lookback_days}d",
            interval="1d",
            auto_adjust=False,
            threads=False,
            progress=False,
        )
        if df is None or df.empty:
            print(f"⚠️ [stocks] Нет данных для {symbol}")
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        out = df.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        })[["open", "high", "low", "close", "volume"]].copy()

        # Приведение времени к UTC
        if out.index.tz is None:
            out.index = out.index.tz_localize("UTC")
        else:
            out.index = out.index.tz_convert("UTC")

        out = out.dropna()

        # Ограничение до последних 320 записей
        if len(out) > 320:
            out = out.iloc[-320:]

        print(f"✅ [stocks] Загружено {len(out)} свечей для {symbol}")
        return out
    except Exception:
        print(f"❌ [stocks] Ошибка при загрузке данных для {symbol}:")
        traceback.print_exc()
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
