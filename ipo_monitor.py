import requests
import datetime
import os
from telegram import Bot
from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN)

def fetch_ipo_data():
    url = "https://www.sec.gov/files/company_tickers_exchange.json"
    try:
        response = requests.get(url)
        if response.ok:
            return response.json()
    except Exception as e:
        return {}

def analyze_with_gpt(text):
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"Дай краткую инвестиционную оценку IPO: {text}. Стоит ли следить за этой компанией?"
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "⚠️ Не удалось получить анализ от GPT."

def send_ipo_alert(ticker, name, date):
    summary = analyze_with_gpt(f"{ticker} ({name}), дата IPO: {date}")
    message = f"📈 Новое IPO:\n— {name} ({ticker})\n— Дата: {date}\n\n🧠 GPT-анализ:\n{summary}"
    bot.send_message(chat_id=CHAT_ID, text=message)

def main():
    ipo_data = fetch_ipo_data()
    today = datetime.date.today().isoformat()

    for item in ipo_data.get("data", []):
        ticker = item.get("ticker", "???")
        name = item.get("name", "Без названия")
        date = item.get("ipoDate", "")
        if date == today:
            send_ipo_alert(ticker, name, date)

if __name__ == "__main__":
    main()
