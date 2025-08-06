import requests
import openai
import os
import json
from time import sleep

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not OPENAI_API_KEY or not BOT_TOKEN or not CHAT_ID:
    raise ValueError("❌ Проверь OPENAI_API_KEY, BOT_TOKEN, CHAT_ID")

CHAT_ID = int(CHAT_ID)
openai.api_key = OPENAI_API_KEY

SEEN_FILE = "coins_seen.json"

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"❌ Ошибка при отправке в Telegram: {e}")

def load_seen_ids():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen_ids(ids):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(ids), f)

def fetch_new_coins():
    print("🔎 Получение списка новых монет...")
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 100, "page": 1}
    response = requests.get(url, params=params)
    if response.ok:
        return response.json()
    return []

def analyze_coin(coin):
    try:
        coin_id = coin["id"]
        info = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}").json()
        name = info.get("name", "")
        description = info.get("description", {}).get("en", "")
        market_data = info.get("market_data", {})
        market_cap = market_data.get("market_cap", {}).get("usd", 0)
        volume = market_data.get("total_volume", {}).get("usd", 0)

        prompt = (
            f"Name: {name}\n"
            f"Market Cap: ${market_cap}\n"
            f"Volume: ${volume}\n"
            f"Description: {description[:500]}\n\n"
            "Give a short investment analysis of this new coin:\n"
            "- Does it have future potential?\n"
            "- Is it risky?\n"
            "- Should investors follow or avoid it?"
        )

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.4
        )

        if response.choices and response.choices[0].message:
            return name, response.choices[0].message.content
        else:
            return name, "⚠️ OpenAI не вернул осмысленный ответ."

    except Exception as e:
        return coin["name"], f"❌ Ошибка OpenAI: {e}"

def run_crypto_analysis():
    try:
        seen_ids = load_seen_ids()
        coins = fetch_new_coins()
        new_coins = [coin for coin in coins if coin["id"] not in seen_ids and coin.get("market_cap", 0) > 1_000_000]

        if not new_coins:
            send_to_telegram("🕵️‍♂️ Нет новых достойных криптовалют на CoinGecko.")
            return

        for coin in new_coins[:2]:
            name, analysis = analyze_coin(coin)
            send_to_telegram(f"🪙 *{name}*\n{analysis}")
            seen_ids.add(coin["id"])
            sleep(1)

        save_seen_ids(seen_ids)

    except Exception as e:
        send_to_telegram(f"❌ Ошибка в run_crypto_analysis: {e}")
