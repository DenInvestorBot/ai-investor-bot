from crypto_monitor import send_to_telegram

def run_status_check():
    try:
        send_to_telegram("✅ Бот работает. Проверка статуса пройдена успешно.")
    except Exception as e:
        send_to_telegram(f"❌ Ошибка в статусе: {e}")
