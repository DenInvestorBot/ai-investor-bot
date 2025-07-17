import requests
import os
from telegram import Bot
from openai import OpenAI

# Подключение переменных окружения
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_new_coins():
    url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
    response = requests.get(url)
    if response.ok:
        coins = response.json()
        return coins[-5:]  # Последние 5 монет
    return []

def analyze_coin(coin_id):
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
        "- Should investors follow or avoid it?\n"
        "- Does it have growth potential in the near future?"
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )

    return name, response.choices[0].message.content

def send_to_telegram(message):
    bot.send_message(chat_id=CHAT_ID, text=message)

def run_crypto_analysis():
    coins = fetch_new_coins()
    for coin in coins:
        coin_id = coin["id"]
        name, analysis = analyze_coin(coin_id)
        send_to_telegram(f"🪙 *{name}*\n{analysis}")
