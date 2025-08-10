# signals/advisor.py
import pandas as pd
import yfinance as yf
import numpy as np

def get_candle_analysis(symbol: str, interval: str = "1d", lookback: int = 60):
    """
    Загружает историю цен и строит простейший анализ свечей + тренда.
    Возвращает dict с рекомендацией.
    """
    df = yf.download(symbol, period=f"{lookback}d", interval=interval, progress=False)
    if df.empty:
        return None

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Тренд
    if last["MA20"] > last["MA50"]:
        trend = "up"
    elif last["MA20"] < last["MA50"]:
        trend = "down"
    else:
        trend = "flat"

    # Свечной паттерн
    body = last["Close"] - last["Open"]
    body_prev = prev["Close"] - prev["Open"]

    action = "hold"
    reason = "net signala"

    if trend == "up" and body > 0 and last["Close"] > prev["High"]:
        action = "buy"
        reason = "probitie vershiny na rostushchem trende"
    elif trend == "down" and body < 0 and last["Close"] < prev["Low"]:
        action = "sell"
        reason = "probitie miniymuma na padaushem trende"
    elif trend == "up" and body < 0:
        action = "wait_pullback"
        reason = "korrektsiya na rostushchem trende"
    elif trend == "down" and body > 0:
        action = "reduce_or_exit"
        reason = "otkat na padaushem trende"

    # Risk-менеджмент (SL/TP по ATR)
    atr = (df["High"] - df["Low"]).rolling(14).mean().iloc[-1]
    sl = None
    tp = None
    rr = None

    if action in ["buy", "sell"]:
        if action == "buy":
            sl = last["Close"] - 1.5 * atr
            tp = last["Close"] + 3 * atr
        elif action == "sell":
            sl = last["Close"] + 1.5 * atr
            tp = last["Close"] - 3 * atr

        rr = abs(tp - last["Close"]) / abs(last["Close"] - sl)

    return {
        "symbol": symbol,
        "trend": trend,
        "action": action,
        "reason": reason,
        "sl": sl,
        "tp": tp,
        "rr": rr,
        "candle_time": last.name
    }

def format_advice(symbol: str, timeframe: str, rec: dict) -> str:
    t = pd.Timestamp(rec["candle_time"]).strftime("%Y-%m-%d")
    a = rec.get("action", "hold")
    reason = rec.get("reason", "—")
    sl = rec.get("sl")
    tp = rec.get("tp")
    rr = rec.get("rr")

    if a == "buy":
        return (
            "Advisor · {symbol} · {tf}\n"
            "Rekomendaciya: POKUPAT (trend up)\n"
            "Prichina: {reason}\n"
            "Urovni: SL={sl:.2f}, TP={tp:.2f} (RR~{rr:.1f})\n"
            "Svecha zakryta: {t}"
        ).format(symbol=symbol, tf=timeframe, reason=reason, sl=sl, tp=tp, rr=rr, t=t)

    if a == "sell":
        return (
            "Advisor · {symbol} · {tf}\n"
            "Rekomendaciya: PRODAVAT/SHORT (trend down)\n"
            "Prichina: {reason}\n"
            "Urovni: SL={sl:.2f}, TP={tp:.2f} (RR~{rr:.1f})\n"
            "Svecha zakryta: {t}"
        ).format(symbol=symbol, tf=timeframe, reason=reason, sl=sl, tp=tp, rr=rr, t=t)

    if a == "reduce_or_exit":
        return (
            "Advisor · {symbol} · {tf}\n"
            "Rekomendaciya: SNIZHAT POZICIIU/VIHODIT (trend down)\n"
            "Prichina: {reason}\n"
            "Svecha zakryta: {t}"
        ).format(symbol=symbol, tf=timeframe, reason=reason, t=t)

    if a == "wait_pullback":
        return (
            "Advisor · {symbol} · {tf}\n"
            "Rekomendaciya: ZHDAT OTKATA (trend up)\n"
            "Prichina: {reason}\n"
            "Svecha zakryta: {t}"
        ).format(symbol=symbol, tf=timeframe, reason=reason, t=t)

    return (
        "Advisor · {symbol} · {tf}\n"
        "Rekomendaciya: NET DEISTVII\n"
        "Prichina: {reason}\n"
        "Svecha zakryta: {t}"
    ).format(symbol=symbol, tf=timeframe, reason=reason, t=t)
