import pandas as pd
import yfinance as yf
import numpy as np
import traceback

print("📄 [signals/advisor] Модуль загружен")

def advise(symbol: str, interval: str = "1d", lookback: int = 60):
    """
    Анализирует свечи и тренд, возвращает dict с рекомендацией.
    """
    try:
        print(f"🚀 [advisor] Загрузка данных для {symbol} ({interval}, {lookback} дней)")
        df = yf.download(symbol, period=f"{lookback}d", interval=interval, progress=False)
        if df.empty or len(df) < 3:
            print(f"⚠️ [advisor] Недостаточно данных для {symbol}")
            return None

        df["MA20"] = df["Close"].rolling(20).mean()
        df["MA50"] = df["Close"].rolling(50).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        # Если скользящие средние не рассчитаны
        if pd.isna(last["MA20"]) or pd.isna(last["MA50"]):
            print(f"⚠️ [advisor] Скользящие средние не рассчитаны для {symbol}")
            return None

        # Определение тренда
        if last["MA20"] > last["MA50"]:
            trend = "up"
        elif last["MA20"] < last["MA50"]:
            trend = "down"
        else:
            trend = "flat"

        # Свечной анализ
        body = last["Close"] - last["Open"]
        body_prev = prev["Close"] - prev["Open"]

        action = "hold"
        reason = "нет сигнала"

        if trend == "up" and body > 0 and last["Close"] > prev["High"]:
            action = "buy"
            reason = "пробитие вершины на растущем тренде"
        elif trend == "down" and body < 0 and last["Close"] < prev["Low"]:
            action = "sell"
            reason = "пробитие минимума на падающем тренде"
        elif trend == "up" and body < 0:
            action = "wait_pullback"
            reason = "коррекция на растущем тренде"
        elif trend == "down" and body > 0:
            action = "reduce_or_exit"
            reason = "откат на падающем тренде"

        # SL/TP расчёт
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
            rr = abs(tp - last["Close"]) / abs(last["Close"] - sl) if sl != last["Close"] else None

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
    except Exception:
        print(f"❌ [advisor] Ошибка в advise() для {symbol}:")
        traceback.print_exc()
        return None

def format_advice(symbol: str, timeframe: str, rec: dict) -> str:
    """Форматирование рекомендации в текст"""
    t = pd.Timestamp(rec["candle_time"]).strftime("%Y-%m-%d")
    a = rec.get("action", "hold")
    reason = rec.get("reason", "—")
    sl = rec.get("sl")
    tp = rec.get("tp")
    rr = rec.get("rr")

    if a == "buy":
        return ("Advisor · {symbol} · {tf}\n"
                "Рекомендация: ПОКУПАТЬ (тренд up)\n"
                "Причина: {reason}\n"
                "Уровни: SL={sl:.2f}, TP={tp:.2f} (RR~{rr:.1f})\n"
                "Свеча закрыта: {t}").format(
                    symbol=symbol, tf=timeframe, reason=reason,
                    sl=sl, tp=tp, rr=rr, t=t)

    if a == "sell":
        return ("Advisor · {symbol} · {tf}\n"
                "Рекомендация: ПРОДАВАТЬ/SHORT (тренд down)\n"
                "Причина: {reason}\n"
                "Уровни: SL={sl:.2f}, TP={tp:.2f} (RR~{rr:.1f})\n"
                "Свеча закрыта: {t}").format(
                    symbol=symbol, tf=timeframe, reason=reason,
                    sl=sl, tp=tp, rr=rr, t=t)

    if a == "reduce_or_exit":
        return ("Advisor · {symbol} · {tf}\n"
                "Рекомендация: СНИЖАТЬ ПОЗИЦИЮ/ВЫХОДИТЬ (тренд down)\n"
                "Причина: {reason}\n"
                "Свеча закрыта: {t}").format(
                    symbol=symbol, tf=timeframe, reason=reason, t=t)

    if a == "wait_pullback":
        return ("Advisor · {symbol} · {tf}\n"
                "Рекомендация: ЖДАТЬ ОТКАТА (тренд up)\n"
                "Причина: {reason}\n"
                "Свеча закрыта: {t}").format(
                    symbol=symbol, tf=timeframe, reason=reason, t=t)

    return ("Advisor · {symbol} · {tf}\n"
            "Рекомендация: НЕТ ДЕЙСТВИЙ\n"
            "Причина: {reason}\n"
            "Свеча закрыта: {t}").format(
                symbol=symbol, tf=timeframe, reason=reason, t=t)
