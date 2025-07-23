from telegram import Bot

BOT_TOKEN = "7913819667:AAFDNAsoSgwA6Y_eTc1zuaP1LoLWNJTLJcQ"  # Подставь свой токен
CHAT_ID = 1634571706  # Твой chat_id

bot = Bot(token=BOT_TOKEN)

def fetch_ipo_data():
    return ["Acme Corp (ACME) — 2025-07-24", "QuantumX (QTX) — 2025-07-25"]

def run_ipo_monitor():
    bot.send_message(chat_id=CHAT_ID, text="📈 Тестовое сообщение от ipo_monitor!")  # <-- Явная проверка
    ipos = fetch_ipo_data()
    if not ipos:
        bot.send_message(chat_id=CHAT_ID, text="⚠️ Сегодня нет новых IPO или произошла ошибка при получении данных.")
    else:
        for ipo in ipos:
            bot.send_message(chat_id=CHAT_ID, text=f"📈 Новое IPO: {ipo}")
