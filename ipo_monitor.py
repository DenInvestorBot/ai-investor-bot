import requests
import datetime
from openai import OpenAI
from telegram import Bot
from config import TELEGRAM_TOKEN, CHAT_ID, OPENAI_API_KEY

bot = Bot(token=TELEGRAM_TOKEN)
openai = OpenAI(api_key=OPENAI_API_KEY)

# Пример API-источника — заменить на свой
IPO_API_URL = "https://financialmodelingprep.com/api/v3/ipo_calendar?apikey=YOUR_API_KEY"

def fetch_real_ipos():
    today = datetime.date.today()
    response = requests.get(IPO_API_URL)
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
        except Exception as e:
            continue

    return real_ipos

def analyze_ipo(ipo):
    prompt = (
        f"Компания: {ipo['companyName']}\n"
        f"Тикер: {ipo['ticker']}\n"
        f"Сектор: {ipo.get('sector', 'не указан')}\n"
        f"Капитализация: неизвестна\n"
        f"Описание: неизвестно\n\n"
        f"Проанализируй инвестиционную привлекательность этой IPO.\n"
        f"Дай краткий обзор перспектив, рисков и кому может быть интересно."
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
        return "AI-анализ временно недоступен."

def send_ipo_report():
    ipos = fetch_real_ipos()
    if not ipos:
        bot.send_message(chat_id=CHAT_ID, text="Сегодня не было новых IPO на бирже.")
        return

    for ipo in ipos:
        text = (
            f"📈 {ipo['companyName']} ({ipo['ticker']})\n"
            f"Дата IPO: {ipo['date']}\n"
            f"Биржа: {ipo['exchange']}\n"
            f"Цена размещения: {ipo['price']}\n"
            f"Сектор: {ipo.get('sector', 'не указан')}\n\n"
        )

        analysis = analyze_ipo(ipo)
        full_message = text + analysis
        bot.send_message(chat_id=CHAT_ID, text=full_message)

if __name__ == "__main__":
    send_ipo_report()
