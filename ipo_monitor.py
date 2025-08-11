import os
import requests
import datetime
from openai import OpenAI
from telegram import Bot
import traceback

print("📄 [ipo_monitor] Модуль загружен")

# ===== Настройка переменных окружения =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID", "0"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
IPO_API_KEY = os.getenv("IPO_API_KEY")

if not TELEGRAM_TOKEN or not CHAT_ID:
    print("⚠️ [ipo_monitor] ВНИМАНИЕ: Не заданы TELEGRAM_TOKEN и/или CHAT_ID — сообщения в Telegram не будут отправляться")
if not OPENAI_API_KEY:
    print("⚠️ [ipo_monitor] ВНИМАНИЕ: Не задан OPENAI_API_KEY — AI-анализ IPO отключён")
if not IPO_API_KEY:
    print("⚠️ [ipo_monitor] ВНИМАНИЕ: Не задан IPO_API_KEY — данные IPO не будут получены")

IPO_API_URL = f"https://financialmodelingprep.com/api/v3/ipo_calendar?apikey={IPO_API_KEY}" if IPO_API_KEY else None
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ===== Функции =====
def fetch_real_ipos():
    """Получение списка реальных IPO"""
    if not IPO_API_URL:
        print("❌ [ipo_monitor] Нет IPO_API_KEY — пропуск запроса")
        return []

    today = datetime.date.today()
    try:
        response = requests.get(IPO_API_URL, timeout=15)
        if not response.ok:
            print(f"⚠️ [ipo_monitor] Ошибка ответа API IPO: {response.status_code}")
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
    except Exception:
        print("❌ [ipo_monitor] Ошибка при получении IPO:")
        traceback.print_exc()
        return []

def analyze_ipo(ipo):
    """Анализ IPO с помощью OpenAI"""
    if not client:
        return "AI-анализ отключён (нет OPENAI_API_KEY)."

    prompt = (
        f"Компания: {ipo['companyName']}\n"
        f"Тикер: {ipo['ticker']}\n"
        f"Сектор: {ipo.get('sector', 'не указан')}\n"
        f"Цена размещения: {ipo.get('price', 'не указана')}\n\n"
        "Проанализируй инвестиционную привлекательность этой IPO. "
        "Укажи плюсы, риски и кому может быть интересно."
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты финансовый аналитик."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ [ipo_monitor] Ошибка AI-анализа IPO {ipo['ticker']}: {e}")
        return f"⚠️ AI-анализ недоступен: {e}"

def run_ipo_monitor():
    """Запуск проверки и анализа IPO"""
    print("🚀 [ipo_monitor] Запуск мониторинга IPO...")

    bot = None
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            bot = Bot(token=TELEGRAM_TOKEN)
        except Exception:
            print("❌ [ipo_monitor] Ошибка инициализации Telegram-бота:")
            traceback.print_exc()

    ipos = fetch_real_ipos()
    if not ipos:
        if bot:
            bot.send_message(chat_id=CHAT_ID, text="Сегодня не было новых IPO на бирже.")
        print("ℹ️ [ipo_monitor] Новых IPO нет")
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

        if bot:
            try:
                bot.send_message(chat_id=CHAT_ID, text=full_message)
            except Exception:
                print("❌ [ipo_monitor] Ошибка отправки IPO в Telegram:")
                traceback.print_exc()
        else:
            print(full_message)
