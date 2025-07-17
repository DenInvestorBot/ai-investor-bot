import requests
import os
from telegram import Bot
from openai import OpenAI

# Получение переменных окружения
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=BOT_TOKEN)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_new_coins():
    url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
    try:
        response = requests.get(url)
        response.raise_for_status()
        coins = response.json()
        return coins[-5:]  # последние 5 добавленных монет
    except Exception as e:
        bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Ошибка при получении списка монет: {e}")
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
    f"🔍 Analyze the potential of this new cryptocurrency:\n\n"
    f"Name: {name}\n"
    f"Market Cap: ${market_cap}\n"
    f"Volume: ${volume}\n\n"
    f"Description: {description[:500]}\n\n"
    f"Should an investor consider buying this coin? "
    f"What are the risks, expected future growth, and long-term potential?"


        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )

        analysis = response.choices[0].message.content.strip()
        return name, analysis

    except Exception as e:
        return name, f"⚠️ GPT-анализ не выполнен: {e}"

def send_to_telegram(message):
    bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")

def run_crypto_analysis():
    coins = fetch_new_coins()
    for coin in coins:
        coin_id = coin["id"]
        name, analysis = analyze_coin(coin_id)
        send_to_telegram(f"🪙 *{name}*\n\n{analysis}")
