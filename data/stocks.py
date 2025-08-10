# data/stocks.py
# Simple daily OHLCV loader for US stocks via yfinance
from __future__ import annotations
import pandas as pd
import yfinance as yf

__all__ = ["load_stock_ohlcv_daily"]

def load_stock_ohlcv_daily(symbol: str, lookback_days: int = 430) -> pd.DataFrame:
    """Return DataFrame with columns [open, high, low, close, volume], UTC index.
    Uses Yahoo Finance daily data. Only closed daily candles."""
    df = yf.download(
        tickers=symbol,
        period=f"{lookback_days}d",
        interval="1d",
        auto_adjust=False,
        threads=False,
        progress=False,
    )
    if df is None or df.empty:
        raise RuntimeError(f"No data for {symbol}")
    out = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"
    })[["open", "high", "low", "close", "volume"]].copy()
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    out = out.dropna()
    if len(out) > 320:
        out = out.iloc[-320:]
    return out
