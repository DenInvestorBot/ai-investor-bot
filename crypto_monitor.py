import requests
import openai
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

openai.api_key = OPENAI_API_KEY

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

def fetch_new_coins():
    url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
    response = requests.get(url)
    if response.ok:
        coins = response.json()
        return coins[-2:]  # Снизим нагрузку — анализируем только 2 последних монеты
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
        "- Should investors follow or avoid it?"
    )

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400
        )
        return name, response.choices[0].message.content
    except openai.RateLimitError:
        send_to_telegram("⚠️ OpenAI: превышен лимит запросов. Попробуй позже или снизь частоту анализа.")
        return name, "⚠️ Анализ временно невозможен: превышен лимит OpenAI."
    except Exception as e:
        send_to_telegram(f"❌ Ошибка OpenAI: {e}")
        return name, f"❌ Ошибка OpenAI: {e}"

def run_crypto_analysis():
    try:
        coins = fetch_new_coins()
        for coin in coins:
            coin_id = coin["id"]
            name, analysis = analyze_coin(coin_id)
            send_to_telegram(f"🪙 *{name}*\n{analysis}")
    except Exception as e:
        send_to_telegram(f"❌ Ошибка в run_crypto_analysis: {e}")
