import requests
import datetime
import os
import openai
from telegram import Bot

# Получаем переменные окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Проверка на обязательные значения
if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не установлен в переменных окружения")
if not CHAT_ID:
    raise ValueError("❌ CHAT_ID не установлен в переменных окружения")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY не установлен в переменных окружения")

# Преобразование типов
CHAT_ID = int(CHAT_ID)
bot = Bot(token=TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY

# API для IPO (укажи свой ключ в ссылке)
IPO_API_URL = "https://financialmodelingprep.com/api/v3/ipo_calendar?apikey=YOUR_API_KEY"

def fetch_real_ipos():
    today = datetime.date.today()
    response = requests.get(IPO_API_URL)
    if not response.ok:
        return []

    ipos = response.json()
    real_ipos = []

    for ipo in ipos:
        try:
            ipo_date = datetime.datetime.strptime(ipo["date"], "%Y-%m-%d").date()
            if (
                ipo_date <= today and
                ipo.get("exchange") in ["NASDAQ", "NYSE"] and
                ipo.get("price") and
                ipo.get("ticker")
            ):
                real_ipos.append(ipo)
        except Exception:
            continue

    return real_ipos

def analyze_ipo(ipo):
    prompt = (
        f"Компания: {ipo['companyName']}\n"
        f"Тикер: {ipo['ticker']}\n"
        f"Сектор: {ipo.get('sector', 'не указан')}\n"
        f"Цена размещения: {ipo.get('price', 'не указана')}\n\n"
        "Проанализируй инвестиционную привлекательность этой IPO. Укажи плюсы, риски и кому может быть интересно."
    )

    try:
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты финансовый аналитик."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ AI-анализ недоступен: {e}"

def run_ipo_monitor():
    ipos = fetch_real_ipos()
    if not ipos:
        bot.send_message(chat_id=CHAT_ID, text="Сегодня не было новых IPO на бирже.")
        return

    for ipo in ipos:
        message = (
            f"📈 {ipo['companyName']} ({ipo['ticker']})\n"
            f"Дата IPO: {ipo['date']}\n"
            f"Биржа: {ipo['exchange']}\n"
            f"Цена размещения: {ipo['price']}\n"
            f"Сектор: {ipo.get('sector', 'не указан')}\n\n"
        )
        analysis = analyze_ipo(ipo)
        full_message = message + analysis
        bot.send_message(chat_id=CHAT_ID, text=full_message)
