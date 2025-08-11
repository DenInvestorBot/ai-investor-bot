import os
from crypto_monitor import send_to_telegram, _escape_markdown

print("📄 [status_check] Модуль загружен")

# ===== Настройка переменных окружения =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID", "0"))

def run_status_check():
    """Проверка работоспособности бота"""
    print("🚀 [status_check] Запуск проверки статуса...")
    if not TELEGRAM_TOKEN or CHAT_ID == 0:
        print("⚠️ [status_check] Нет TELEGRAM_TOKEN или CHAT_ID — пропуск отправки статуса")
        return

    try:
        send_to_telegram(_escape_markdown("✅ Бот работает. Проверка статуса пройдена успешно."))
        print("✅ [status_check] Сообщение о статусе отправлено")
    except Exception as e:
        send_to_telegram(_escape_markdown(f"❌ Ошибка в статусе: {e}"))
        print(f"❌ [status_check] Ошибка при отправке статуса: {e}")
