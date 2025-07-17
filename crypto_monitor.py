import requests
import openai
import os
from telegram import Bot

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def fetch_new_coins():
    url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
    response = requests.get(url)
    data = response.json()

    if isinstance(data, list):
        return data[-5:]  # Возвращаем последние 5 монет
    else:
        return []

def analyze_coin(coin_id):
    info = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}").json()
    name = info.get("name", "")
    description = info.get("description", {}).get("en", "")
    market_data = info.get("market_data", {})
    market_cap = market_data.get("market_cap", {}).get("usd", 0)
    volume = market_data.get("total_volume", {}).get("usd", 0)

    prompt = f"Analyze the potential of this new coin:\n\nName: {name}\nMarket Cap: ${market_cap}\nVolume: ${volume}\n\nDescription: {description[:1000]}"
    openai.api_key = OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    return name, response.choices[0].message["content"]

def send_to_telegram(message):
    Bot(token=BOT_TOKEN).send_message(chat_id=CHAT_ID, text=message)

def run_crypto_analysis():
    coins = fetch_new_coins()
    for coin in coins:
        coin_id = coin["id"]
        name, analysis = analyze_coin(coin_id)
        send_to_telegram(f"🪙 *{name}*\n{analysis}")
