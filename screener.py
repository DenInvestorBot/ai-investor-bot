import os
import time
import math
import json
import logging
from typing import Dict, List, Any
import requests

from screener_config import ScreenerConfig

logger = logging.getLogger("screener")
logging.basicConfig(level=logging.INFO)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex"

STATE_FILE = "screener_state.json"  # чтобы не спамить одинаковыми алертами

def _headers(cfg: ScreenerConfig) -> Dict[str, str]:
    h = {"accept": "application/json"}
    if cfg.coingecko_api_key and not cfg.coingecko_api_key.startswith("${"):
        h["x-cg-pro-api-key"] = cfg.coingecko_api_key
    return h

def load_state() -> Dict[str, Any]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"last_alerted": {}}
    return {"last_alerted": {}}

def save_state(state: Dict[str, Any]):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def fetch_markets_page(cfg: ScreenerConfig, page: int) -> List[Dict[str, Any]]:
    params = {
        "vs_currency": "usd",
        "order": "market_cap_asc",
        "per_page": cfg.coingecko_per_page,
        "page": page,
        "sparkline": "false",
        "price_change_percentage": "1h,24h,7d,30d",
        "locale": "en",
    }
    resp = requests.get(f"{COINGECKO_BASE}/coins/markets", params=params, headers=_headers(cfg), timeout=30)
    resp.raise_for_status()
    return resp.json()

def fetch_market_chart(cfg: ScreenerConfig, coin_id: str, days: int = 7) -> Dict[str, Any]:
    params = {"vs_currency": "usd", "days": days, "interval": "hourly"}
    r = requests.get(f"{COINGECKO_BASE}/coins/{coin_id}/market_chart", params=params, headers=_headers(cfg), timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_dexscreener_trending() -> List[Dict[str, Any]]:
    try:
        r = requests.get(f"{DEXSCREENER_BASE}/tokens", timeout=20)
        if r.status_code == 200:
            data = r.json()
            return data.get("tokens", [])
    except Exception as e:
        logger.warning(f"DexScreener fetch failed: {e}")
    return []

def normalize_platforms(platforms: Dict[str, Any]) -> List[str]:
    if not platforms:
        return []
    names = []
    for k, v in platforms.items():
        if k:
            names.append(k.lower())
    return names

def base_filters(cfg: ScreenerConfig, c: Dict[str, Any]) -> bool:
    price = c.get("current_price") or 0
    mcap = c.get("market_cap") or 0
    vol = c.get("total_volume") or 0
    if price <= 0 or vol is None:
        return False
    if cfg.price_max and price > cfg.price_max:
        return False
    if cfg.market_cap_max and (mcap is None or mcap > cfg.market_cap_max):
        return False
    if cfg.volume_min and vol < cfg.volume_min:
        return False
    if cfg.allowed_platforms:
        platforms = normalize_platforms(c.get("platforms") or {})
        if platforms:
            if not any(p in platforms for p in [x.lower() for x in cfg.allowed_platforms]):
                return False
    return True

def momentum_score(cfg: ScreenerConfig, c: Dict[str, Any], vol_spike_ratio: float = 1.0) -> float:
    ch1h = (c.get("price_change_percentage_1h_in_currency") or 0) / 100.0
    ch24 = (c.get("price_change_percentage_24h_in_currency") or 0) / 100.0
    ch7d = (c.get("price_change_percentage_7d_in_currency") or 0) / 100.0
    score = 0
    score += ch1h * 2.0
    score += ch24 * 1.0
    score += ch7d * 0.5
    score += max(0.0, (vol_spike_ratio - 1.0)) * 0.5
    return score

def volume_spike_from_chart(chart: Dict[str, Any]) -> float:
    volumes = [v for t, v in chart.get("total_volumes", [])]
    if not volumes:
        return 1.0
    last = volumes[-1]
    avg7d = sum(volumes[:-1]) / max(1, len(volumes) - 1)
    return (last / avg7d) if avg7d > 0 else 1.0

def send_telegram(token: str, chat_id: str, text: str):
    if not token or token.startswith("${"):
        logger.info("Telegram token not set — skip send")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")

def run_screener(cfg: ScreenerConfig):
    state = load_state()
    last_alerted = state.get("last_alerted", {})

    candidates: List[Dict[str, Any]] = []

    # 1) тянем страницы рынков от меньшей капы
    for page in range(1, cfg.coingecko_pages + 1):
        data = fetch_markets_page(cfg, page)
        for c in data:
            try:
                if base_filters(cfg, c):
                    candidates.append(c)
            except Exception as e:
                logger.debug(f"skip coin: {e}")
        time.sleep(1)

    # 2) добавим горячие DEX-кандидаты (если включено)
    if cfg.use_dexscreener:
        try:
            ds = fetch_dexscreener_trending()
            for t in ds[:100]:
                symbol = t.get("symbol") or (t.get("baseToken") or {}).get("symbol")
                if not symbol:
                    continue
                c = {
                    "id": f"dexscreener:{t.get('address','unknown')}",
                    "symbol": symbol,
                    "name": t.get("name", symbol),
                    "current_price": float(t.get("priceUsd") or 0) if t.get("priceUsd") else 0,
                    "market_cap": None,
                    "total_volume": float(t.get("fdv") or 0) * 0.05 if t.get("fdv") else 0,
                    "platforms": { (t.get("chainId") or ""): t.get("address") },
                    "price_change_percentage_1h_in_currency": None,
                    "price_change_percentage_24h_in_currency": None,
                    "price_change_percentage_7d_in_currency": None,
                    "_source": "dexscreener",
                }
                if base_filters(cfg, c):
                    candidates.append(c)
        except Exception as e:
            logger.warning(f"DexScreener enrich failed: {e}")

    # 3) топ по 24h изменению -> считаем vol spike
    def ch24(c):
        return c.get("price_change_percentage_24h_in_currency") or -9999

    top = sorted(candidates, key=ch24, reverse=True)[: cfg.deep_candidates]

    scored = []
    for c in top:
        coin_id = c.get("id")
        vol_spike = 1.0
        if coin_id and not str(coin_id).startswith("dexscreener:"):
            try:
                chart = fetch_market_chart(cfg, coin_id, days=7)
                vol_spike = volume_spike_from_chart(chart)
            except Exception:
                vol_spike = 1.0
            time.sleep(0.5)
        s = momentum_score(cfg, c, vol_spike)
        c["_vol_spike"] = vol_spike
        c["_score"] = s
        scored.append(c)

    # 4) shortlist: зона запуска
    shortlist = []
    for c in scored:
        ch1 = c.get("price_change_percentage_1h_in_currency") or 0
        ch24p = c.get("price_change_percentage_24h_in_currency") or 0
        vol_spike = c.get("_vol_spike", 1.0)
        if (ch1 >= cfg.min_change_1h_pct) or (ch24p >= cfg.min_change_24h_pct) or (vol_spike >= cfg.min_volume_spike_ratio):
            shortlist.append(c)

    shortlist = sorted(shortlist, key=lambda x: x.get("_score", 0), reverse=True)[:20]

    alerts = []
    now_ts = time.time()
    for c in shortlist:
        coin_key = f"{(c.get('symbol') or '').upper()}::{c.get('id')}"
        last_ts = last_alerted.get(coin_key, 0)
        if now_ts - last_ts < 60 * 60:  # не чаще раза в час
            continue
        msg = format_alert(c)
        alerts.append((coin_key, msg))

    if alerts and cfg.enable_telegram_alerts:
        for coin_key, msg in alerts:
            send_telegram(cfg.telegram_bot_token, cfg.telegram_chat_id, msg)
            last_alerted[coin_key] = now_ts
        state["last_alerted"] = last_alerted
        save_state(state)

    return {
        "checked": len(candidates),
        "alerts": len(alerts),
        "top_examples": [fmt_console_row(x) for x in shortlist[:5]],
    }

def fmt_console_row(c: Dict[str, Any]) -> str:
    sym = (c.get("symbol") or "").upper()
    name = c.get("name") or sym
    price = c.get("current_price") or 0
    ch1 = c.get("price_change_percentage_1h_in_currency") or 0
    ch24p = c.get("price_change_percentage_24h_in_currency") or 0
    ch7 = c.get("price_change_percentage_7d_in_currency") or 0
    s = c.get("_score", 0)
    return f"{name} ({sym}) | ${price:.6f} | 1h {ch1:.2f}% | 24h {ch24p:.2f}% | 7d {ch7:.2f}% | score {s:.3f}"

def format_alert(c: Dict[str, Any]) -> str:
    sym = (c.get("symbol") or "").upper()
    name = c.get("name") or sym
    price = c.get("current_price") or 0
    ch1 = c.get("price_change_percentage_1h_in_currency") or 0
    ch24p = c.get("price_change_percentage_24h_in_currency") or 0
    vol_spike = c.get("_vol_spike", 1.0)
    source = c.get("_source", "coingecko")
    lines = [
        f"<b>🎯 Зона запуска:</b> <b>{name} ({sym})</b>",
        f"Цена: <b>${price:.6f}</b> | 1ч: <b>{ch1:.2f}%</b> | 24ч: <b>{ch24p:.2f}%</b>",
        f"Спайк объёма: <b>{vol_spike:.2f}×</b> | Источник: <code>{source}</code>",
        "Фильтры: цена≤$0.10, капа≤$100M, объём≥$10M (ред.)",
    ]
    return "\n".join(lines)

if __name__ == "__main__":
    cfg = ScreenerConfig()
    res = run_screener(cfg)
    print(json.dumps(res, ensure_ascii=False, indent=2))
