import os
import json
import re
from time import sleep

import requests
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not OPENAI_API_KEY or not BOT_TOKEN or not CHAT_ID:
    raise ValueError("❌ Проверь переменные окружения: OPENAI_API_KEY, BOT_TOKEN, CHAT_ID")

CHAT_ID = int(CHAT_ID)
client = OpenAI(api_key=OPENAI_API_KEY)

SEEN_FILE = "coins_seen.json"

# --------- Telegram helpers ---------
def _escape_markdown(text: str) -> str:
    # Безопасное экранирование для Markdown
    # Экранируем самые частые проблемные символы
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

def send_to_telegram(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=data, timeout=15)
    except Exception as e:
        print(f"❌ Ошибка при отправке в Telegram: {e}")

# --------- Seen IDs persistence ---------
def load_seen_ids():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen_ids(ids):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(list(ids), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Не удалось сохранить {SEEN_FILE}: {e}")

# --------- CoinGecko ---------
def fetch_top_market_coins():
    """
    Это не 'новые' монеты, а топ по капе.
    Оставляем как есть (по твоей логике), но с таймаутом и защитой.
    """
    print("🔎 Получение списка монет (market_cap_desc)...")
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 100, "page": 1}
    try:
        response = requests.get(url, params=params, timeout=20)
        if response.ok:
            return response.json()
    except Exception as e:
        print(f"❌ CoinGecko ошибка: {e}")
    return []

def fetch_coin_details(coin_id: str):
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}",
            params={"localization": "false"},
            timeout=20
        )
        if r.ok:
            return r.json()
    except Exception as e:
        print(f"❌ CoinGecko details ошибка: {e}")
    return {}

# --------- AI ---------
def analyze_coin(coin):
    try:
        coin_id = coin.get("id")
        info = fetch_coin_details(coin_id)
        name = info.get("name", coin.get("name", ""))
        description = (info.get("description", {}) or {}).get("en", "")[:600]
        market_data = info.get("market_data", {}) or {}
        market_cap = (market_data.get("market_cap", {}) or {}).get("usd", 0)
        volume = (market_data.get("total_volume", {}) or {}).get("usd", 0)
        homepage = ""
        try:
            homepage = (info.get("links", {}) or {}).get("homepage", [""])[0] or ""
        except Exception:
            pass

        prompt = (
            "You are an investment analyst. Give a concise, actionable view.\n"
            "Return max 7 concise bullet points in English.\n\n"
            f"Name: {name}\n"
            f"Market Cap (USD): {market_cap}\n"
            f"24h Volume (USD): {volume}\n"
            f"Website: {homepage}\n"
            f"Description: {description}\n\n"
            "Focus on: utility, traction, token economics, key risks, red flags, "
            "and whether it’s worth putting on a watchlist."
        )

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.4,
        )

        content = completion.choices[0].message.content.strip() if completion.choices else ""
        return name, (content or "⚠️ AI не вернул осмысленный ответ.")
    except Exception as e:
        return coin.get("name", "Unknown"), f"❌ Ошибка AI: {e}"

# --------- Orchestrator ---------
def run_crypto_analysis():
    try:
        seen_ids = load_seen_ids()
        coins = fetch_top_market_coins()

        # Твоя логика: считаем 'новыми достойными' те, кого ещё не отправляли и у кого капа > $1M
        new_coins = [
            c for c in coins
            if c.get("id") not in seen_ids and (c.get("market_cap") or 0) > 1_000_000
        ]

        if not new_coins:
            send_to_telegram(_escape_markdown("🕵️‍♂️ Нет новых достойных криптовалют на CoinGecko."))
            return

        for coin in new_coins[:2]:  # ограничим до 2, как у тебя
            name, analysis = analyze_coin(coin)
            msg = f"🪙 *{_escape_markdown(name)}*\n{_escape_markdown(analysis)}"
            send_to_telegram(msg)
            seen_ids.add(coin.get("id"))
            sleep(1)

        save_seen_ids(seen_ids)

    except Exception as e:
        send_to_telegram(_escape_markdown(f"❌ Ошибка в run_crypto_analysis: {e}"))
