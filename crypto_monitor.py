import requests
import openai
import os
from telegram import Bot
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_new_coins():
    url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
    response = requests.get(url)
    coins = response.json()
    if isinstance(coins, list):
        return coins[-5:]
    return []

def analyze_coin(coin_id):
    info = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}").json()
    name = info.get("name", "")
    description = info.get("description", {}).get("en", "")
    market_data = info.get("market_data", {})
    market_cap = market_data.get("market_cap", {}).get("usd", 0)
    volume = market_data.get("total_volume", {}).get("usd", 0)

    prompt = f"Analyze the potential of this new coin:

Name: {name}
Market Cap: ${market_cap}
Volume: ${volume}

Description: {description[:1000]}"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    return name, response.choices[0].message.content.strip()

def send_to_telegram(message):
    Bot(token=BOT_TOKEN).send_message(chat_id=CHAT_ID, text=message)

def run_crypto_analysis():
    coins = fetch_new_coins()
    for coin in coins:
        coin_id = coin["id"]
        name, analysis = analyze_coin(coin_id)
        send_to_telegram(f"🪙 *{name}*
{analysis}")