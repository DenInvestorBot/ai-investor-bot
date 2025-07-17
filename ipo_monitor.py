import requests
import datetime
import os
from telegram import Bot
import openai

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FMP_API_KEY = os.getenv("FMP_API_KEY")

bot = Bot(token=BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

def fetch_today_ipos():
    today = datetime.date.today().isoformat()
    url = f"https://financialmodelingprep.com/api/v3/ipo_calendar?from={today}&to={today}&apikey={FMP_API_KEY}"
    try:
        response = requests.get(url)
        if response.ok:
            return response.json().get("ipoCalendar", [])
    except Exception as e:
        pass
    return []  

def analyze_with_gpt(text):
    prompt = f"Дай краткую инвестиционную оценку IPO: {text}. Стоит ли следить за этой компанией?"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        return "⚠️ Не удалось получить анализ от GPT."

def send_ipo_alert(name, symbol, exchange, date):
    summary = analyze_with_gpt(f"{name} ({symbol}), биржа: {exchange}, дата IPO: {date}")
    message = (
        f"📈 Новое IPO:\n"
        f"— Компания: {name} ({symbol})\n"
        f"— Биржа: {exchange}\n"
        f"— Дата: {date}\n\n"
        f"🧠 GPT-анализ:\n{summary}"
    )
    bot.send_message(chat_id=CHAT_ID, text=message)

def main():
    ipos = fetch_today_ipos()
    for ipo in ipos:
        name = ipo.get("company", "Без названия")
        symbol = ipo.get("symbol", "???")
        exchange = ipo.get("exchange", "Неизвестно")
        date = ipo.get("date", "Неизвестно")
        send_ipo_alert(name, symbol, exchange, date)

if __name__ == "__main__":
    main()
