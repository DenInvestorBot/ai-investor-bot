# signals/advisor.py
# Daily advisor logic (trend filter + candle trigger + ATR levels)
from __future__ import annotations
import numpy as np
import pandas as pd

__all__ = ["advise", "format_advice"]

def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def slope(series: pd.Series, n: int = 5) -> pd.Series:
    base = series.shift(n)
    return (series - base) / (base.replace(0, np.nan))

def bullish_engulf(o, h, l, c):
    po, pc = o.shift(1), c.shift(1)
    return (pc < po) & (c > o) & (o <= pc) & (c >= po)

def bearish_engulf(o, h, l, c):
    po, pc = o.shift(1), c.shift(1)
    return (pc > po) & (c < o) & (o >= pc) & (c <= po)

def hammer(o, h, l, c, tail=0.6):
    body = (c - o).abs()
    rng = (h - l).replace(0, np.nan)
    lower = (np.minimum(o, c) - l)
    upper = (h - np.maximum(o, c))
    return (lower / rng >= tail) & (upper / rng <= 1 - tail) & (body / rng <= 0.4)

def shooting_star(o, h, l, c, tail=0.6):
    body = (c - o).abs()
    rng = (h - l).replace(0, np.nan)
    lower = (np.minimum(o, c) - l)
    upper = (h - np.maximum(o, c))
    return (upper / rng >= tail) & (lower / rng <= 1 - tail) & (body / rng <= 0.4)

def advise(df: pd.DataFrame,
           use_volume: bool = True,
           vol_mult: float = 1.2,
           sl_atr_mult: float = 1.5,
           rr: float = 3.0) -> dict:
    """
    Input: df with columns [open,high,low,close,volume] (closed candles only)
    Output: dict with action & levels for the last candle
    """
    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        raise ValueError(f"df must have columns {required}")

    o, h, l, c, v = [df[k].astype(float) for k in ["open", "high", "low", "close", "volume"]]
    work = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v}).copy()

    work["ema200"] = ema(c, 200)
    work["ema50"] = ema(c, 50)
    work["ema20"] = ema(c, 20)
    work["atr"] = atr(work, 14)
    if use_volume:
        work["vma20"] = v.rolling(20).mean()

    i = len(work) - 1
    if i < 210 or work[["ema200", "ema50", "ema20", "atr"]].iloc[i].isna().any():
        return {"action": "wait", "reason": "недостаточно данных для надёжного сигнала"}

    up = (c.iloc[i] > work["ema200"].iloc[i]) and \
         (work["ema20"].iloc[i] > work["ema50"].iloc[i]) and \
         (slope(work["ema20"]).iloc[i] > 0) and (slope(work["ema50"]).iloc[i] > 0)

    down = (c.iloc[i] < work["ema200"].iloc[i]) and \
           (work["ema20"].iloc[i] < work["ema50"].iloc[i]) and \
           (slope(work["ema20"]).iloc[i] < 0) and (slope(work["ema50"]).iloc[i] < 0)

    vol_ok = True
    if use_volume and not np.isnan(work["vma20"].iloc[i]):
        vol_ok = v.iloc[i] > vol_mult * work["vma20"].iloc[i]

    bull = (bullish_engulf(o, h, l, c) | hammer(o, h, l, c)).iloc[i]
    bear = (bearish_engulf(o, h, l, c) | shooting_star(o, h, l, c)).iloc[i]

    atrv = float(work["atr"].iloc[i]); price = float(c.iloc[i])

    if up and bull and vol_ok:
        sl = price - sl_atr_mult * atrv
        tp = price + rr * (price - sl)
        return {"action": "buy", "trend": "up", "reason": "trend↑ + бычий паттерн" + (" + объём" if use_volume else ""),
                "entry": price, "sl": sl, "tp": tp, "rr": rr}

    if down and bear and vol_ok:
        sl = price + sl_atr_mult * atrv
        tp = price - rr * (sl - price)
        return {"action": "sell", "trend": "down", "reason": "trend↓ + медв. паттерн" + (" + объём" if use_volume else ""),
                "entry": price, "sl": sl, "tp": tp, "rr": rr}

    if down and not bear:
        return {"action": "reduce_or_exit", "trend": "down", "reason": "устойчивый даунтренд, свечного подтверждения нет"}

    if up and not bull:
        return {"action": "wait_pullback", "trend": "up", "reason": "тренд вверх, ждём подтверждения"}

    return {"action": "wait", "reason": "нет совокупного сигнала"}

def format_advice(symbol: str, timeframe: str, rec: dict, candle_time) -> str:
    t = pd.Timestamp(candle_time).strftime("%Y-%m-%d")
    a = rec.get("action", "wait")
    if a == "buy":
        return (f"🤖 Советник · {symbol} · {timeframe}\n"
                f"Рекомендация: ПОКУПАТЬ (тренд ↑)\n"
                f"Причина: {rec['reason']}\n"
                f"Уровни: SL={rec['sl']:.2f}, TP={rec['tp']:.2f} (R
