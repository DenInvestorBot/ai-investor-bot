import os
import json
import re
import traceback
from time import sleep
import requests
from openai import OpenAI

print("📄 [crypto_monitor] Модуль загружен")

# ===== Настройка переменных окружения =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID", "0"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not CHAT_ID:
    print("⚠️ [crypto_monitor] ВНИМАНИЕ: Не заданы TELEGRAM_TOKEN и/или CHAT_ID")
if not OPENAI_API_KEY:
    print("⚠️ [crypto_monitor] ВНИМАНИЕ: Не задан OPENAI_API_KEY — AI-анализ отключён")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
SEEN_FILE = "coins_seen.json"

# ===== Вспомогательные функции =====
def _escape_markdown(text: str) -> str:
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

def send_to_telegram(message: str):
    """Отправка сообщения в Telegram"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ [crypto_monitor] Невозможно отправить сообщение — нет токена или chat_id")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, data=data, timeout=15)
        print(f"📨 [crypto_monitor] Отправлено в Telegram: {message[:60]}...")
    except Exception:
        print("❌ [crypto_monitor] Ошибка при отправке в Telegram:")
        traceback.print_exc()

def load_seen_ids():
    try:
        if os.path.exists(SEEN_FILE):
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                ids = set(json.load(f))
                print(f"📂 [crypto_monitor] Загружено {len(ids)} известных монет")
                return ids
    except Exception:
        print("⚠️ [crypto_monitor] Не удалось загрузить seen_ids:")
        traceback.print_exc()
    return set()

def save_seen_ids(ids):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(list(ids), f, ensure_ascii=False, indent=2)
        print(f"💾 [crypto_monitor] Сохранено {len(ids)} монет в seen_ids")
    except Exception:
        print("⚠️ [crypto_monitor] Не удалось сохранить seen_ids:")
        traceback.print_exc()

def fetch_top_market_coins():
    print("🔎 [crypto_monitor] Получение списка монет...")
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 100, "page": 1}
    try:
        response = requests.get(url, params=params, timeout=20)
        if response.ok:
            coins = response.json()
            print(f"✅ [crypto_monitor] Получено {len(coins)} монет")
            return coins
        print(f"⚠️ [crypto_monitor] Ошибка ответа CoinGecko: {response.status_code}")
    except Exception:
        print("❌ [crypto_monitor] Ошибка при запросе CoinGecko:")
        traceback.print_exc()
    return []

def fetch_coin_details(coin_id: str):
    print(f"🔍 [crypto_monitor] Получение деталей монеты {coin_id}")
    try:
        r = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}",
                         params={"localization": "false"}, timeout=20)
        if r.ok:
            return r.json()
        print(f"⚠️ [crypto_monitor] Не удалось получить {coin_id}: {r.status_code}")
    except Exception:
        print(f"❌ [crypto_monitor] Ошибка при получении {coin_id}:")
        traceback.print_exc()
    return {}

def analyze_coin(coin):
    """AI-анализ монеты"""
    try:
        coin_id = coin.get("id")
        info = fetch_coin_details(coin_id)
        name = info.get("name", coin.get("name", ""))
        description = (info.get("description", {}) or {}).get("en", "")[:600]
        market_data = info.get("market_data", {}) or {}
        market_cap = (market_data.get("market_cap", {}) or {}).get("usd", 0)
        volume = (market_data.get("total_volume", {}) or {}).get("usd", 0)

        prompt = (
            f"Name: {name}\nMarket Cap (USD): {market_cap}\nVolume (USD): {volume}\nDescription: {description}\n"
            "Give a short investment analysis."
        )

        if not client:
            return name, "AI-анализ отключён (нет OPENAI_API_KEY)"

        print(f"🤖 [crypto_monitor] AI-анализ монеты {name}")
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.4,
        )
        return name, completion.choices[0].message.content.strip()
    except Exception:
        print(f"❌ [crypto_monitor] Ошибка при анализе монеты {coin.get('id')}:")
        traceback.print_exc()
        return coin.get("name", "Unknown"), "Ошибка анализа"

# ===== Главная функция (новое имя!) =====
def run_crypto_monitor():
    print("🚀 [crypto_monitor] Запуск анализа криптовалют...")
    try:
        seen_ids = load_seen_ids()
        coins = fetch_top_market_coins()
        new_coins = [
            c for c in coins if c.get("id") not in seen_ids and (c.get("market_cap") or 0) > 1_000_000
        ]
        print(f"📊 [crypto_monitor] Найдено {len(new_coins)} новых монет")

        if not new_coins:
            send_to_telegram(_escape_markdown("🕵️‍♂️ Нет новых достойных криптовалют"))
            return

        for coin in new_coins[:2]:
            name, analysis = analyze_coin(coin)
            send_to_telegram(f"🪙 *{_escape_markdown(name)}*\n{_escape_markdown(analysis)}")
            seen_ids.add(coin.get("id"))
            sleep(1)

        save_seen_ids(seen_ids)
        print("✅ [crypto_monitor] Анализ криптовалют завершён")
    except Exception:
        print("❌ [crypto_monitor] Ошибка в run_crypto_monitor:")
        traceback.print_exc()
