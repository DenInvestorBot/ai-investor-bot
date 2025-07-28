import requests
import openai
import os
import json
from time import sleep

# ENV-переменные
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

# OpenAI ключ
openai.api_key = OPENAI_API_KEY

# Файл для отслеживания уже обработанных монет
SEEN_FILE = "coins_seen.json"

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
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
    url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
    response = requests.get(url)
    if response.ok:
        return response.json()
    return []

def analyze_coin(coin_id):
    try:
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
        return name, response.choices[0].message.content

    except openai.RateLimitError:
        return coin_id, "⚠️ OpenAI: превышен лимит запросов. Попробуй позже."
    except Exception as e:
        return coin_id, f"❌ Ошибка OpenAI: {e}"

def run_crypto_analysis():
    try:
        seen_ids = load_seen_ids()
        coins = fetch_new_coins()
        new_coins = [coin for coin in coins if coin["id"] not in seen_ids]

        if not new_coins:
            send_to_telegram("🕵️‍♂️ Нет новых криптовалют на CoinGecko.")
            return

        for coin in new_coins[:2]:  # Анализируем максимум 2 монеты в день
            coin_id = coin["id"]
            name, analysis = analyze_coin(coin_id)
            send_to_telegram(f"🪙 *{name}*\n{analysis}")
            seen_ids.add(coin_id)
            sleep(1)  # чтобы не получить блокировку по лимиту API

        save_seen_ids(seen_ids)

    except Exception as e:
        send_to_telegram(f"❌ Ошибка в run_crypto_analysis: {e}")

if __name__ == "__main__":
    run_crypto_analysis()
