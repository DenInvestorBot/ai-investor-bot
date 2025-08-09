from crypto_monitor import send_to_telegram, _escape_markdown

def run_status_check():
    try:
        send_to_telegram(_escape_markdown("✅ Бот работает. Проверка статуса пройдена успешно."))
    except Exception as e:
        send_to_telegram(_escape_markdown(f"❌ Ошибка в статусе: {e}"))
