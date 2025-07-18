import requests
import os
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = Bot(token=BOT_TOKEN)

def fetch_ipo_data():
    # Тут должен быть реальный источник IPO. Сейчас — заглушка.
    return []

def run_ipo_monitor():
    ipos = fetch_ipo_data()
    if not ipos:
        bot.send_message(chat_id=CHAT_ID, text="⚠️ Сегодня нет новых IPO или произошла ошибка при получении данных.")
    else:
        for ipo in ipos:
            bot.send_message(chat_id=CHAT_ID, text=f"📈 Новое IPO: {ipo}")
