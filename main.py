import os
import requests
import logging
import schedule
import time
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = Bot(token=BOT_TOKEN)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Храним ID последних криптовалют
seen_ids = set()

def fetch_new_coins():
    try:
        url = "https://api.coingecko.com/api/v3/coins/list?include_platform=false"
        response = requests.get(url)
        coins = response.json()

        new_coins = []
        for coin in coins[-5:]:  # Смотрим последние 5 (можно больше)
            if coin["id"] not in seen_ids:
                seen_ids.add(coin["id"])
                new_coins.append(coin)

        for coin in new_coins:
            msg = f"🆕 Новая криптовалюта на CoinGecko:\n\n🔸 Название: {coin['name']}\n🔹 Символ: {coin['symbol']}\n🔗 ID: {coin['id']}"
            bot.send_message(chat_id=CHAT_ID, text=msg)

    except Exception as e:
        logger.error(f"Ошибка при получении данных: {e}")

def main_loop():
    schedule.every(5).minutes.do(fetch_new_coins)
    logger.info("Бот запущен и следит за новыми криптовалютами...")

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    main_loop()
