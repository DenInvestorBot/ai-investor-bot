import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)

def fetch_ipo_data():
    # Для теста: фиктивные IPO
    return ["Acme Corp (ACME) — 2025-07-24", "QuantumX (QTX) — 2025-07-25"]

def run_ipo_monitor():
    ipos = fetch_ipo_data()
    if not ipos:
        send_to_telegram("⚠️ Сегодня нет новых IPO или произошла ошибка при получении данных.")
    else:
        for ipo in ipos:
            send_to_telegram(f"📈 Новое IPO: {ipo}")
