import requests
import datetime
import os
import openai
from telegram import Bot

IPO_API_KEY = os.getenv("IPO_API_KEY")
IPO_API_URL = f"https://financialmodelingprep.com/api/v3/ipo_calendar?apikey={IPO_API_KEY}"

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

def analyze_ipo(ipo, openai_api_key):
    openai.api_key = openai_api_key

    prompt = (
        f"Компания: {ipo['companyName']}\n"
        f"Тикер: {ipo['ticker']}\n"
        f"Сектор: {ipo.get('sector', 'не указан')}\n"
        f"Цена размещения: {ipo.get('price', 'не указана')}\n\n"
        "Проанализируй инвестиционную привлекательность этой IPO. "
        "Укажи плюсы, риски и кому может быть интересно."
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
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
    CHAT_ID = os.getenv("CHAT_ID")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    if not TELEGRAM_TOKEN or not CHAT_ID or not OPENAI_API_KEY:
        raise ValueError("❌ Не заданы переменные окружения")

    CHAT_ID = int(CHAT_ID)
    bot = Bot(token=TELEGRAM_TOKEN)

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
        analysis = analyze_ipo(ipo, OPENAI_API_KEY)
        full_message = message + analysis
        bot.send_message(chat_id=CHAT_ID, text=full_message)
