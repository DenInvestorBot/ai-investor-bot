import requests
import datetime
import os
from telegram import Bot
import openai

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FMP_API_KEY = os.getenv("FMP_API_KEY")

# Инициализация
bot = Bot(token=BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

# Получение данных IPO
def fetch_today_ipos():
    today = datetime.date.today().isoformat()
    url = f"https://financialmodelingprep.com/api/v3/ipo_calendar?from={today}&to={today}&apikey={FMP_API_KEY}"
    try:
        response = requests.get(url)
        if response.ok:
            return response.json().get("ipoCalendar", [])
    except Exception as e:
        print(f"⚠️ Ошибка при получении IPO данных: {e}")
    return []

# Анализ через GPT
def analyze_with_gpt(text):
    prompt = f"Дай краткую инвестиционную оценку IPO: {text}. Стоит ли следить за этой компанией?"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        return "⚠️ Не удалось получить анализ от GPT."

# Отправка в Telegram
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

# Основной запуск
def run_ipo_monitor():
    ipos = fetch_today_ipos()

    if not ipos:
        print("⚠️ Сегодня нет новых IPO или произошла ошибка при получении данных.")
        return

    for ipo in ipos:
        name = ipo.get("company", "Без названия")
        symbol = ipo.get("symbol", "???")
        exchange = ipo.get("exchange", "Неизвестно")
        date = ipo.get("date", "Неизвестно")
        send_ipo_alert(name, symbol, exchange, date)
