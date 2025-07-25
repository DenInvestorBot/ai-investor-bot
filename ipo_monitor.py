import os
import requests
import openai

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"❌ Ошибка при отправке в Telegram: {e}")

def fetch_ipo_data():
    """
    Здесь — пример с реальными (или тестовыми) данными.
    Реальный парсер можешь подставить по аналогии.
    Каждый IPO — tuple: (name, ticker, date, sector, cap, description)
    """
    return [
        ("Acme Corp", "ACME", "2025-07-24", "Tech", 1_000_000_000, "Acme разрабатывает инновационные платформы для автоматизации бизнеса."),
        ("QuantumX", "QTX", "2025-07-25", "Healthcare", 700_000_000, "QuantumX — биотехнологическая компания нового поколения, специализируется на ИИ и big data в медицине."),
    ]

def analyze_ipo(name, ticker, date, sector, cap, description):
    prompt = (
        f"IPO: {name} ({ticker})\n"
        f"Сектор: {sector}\n"
        f"Капитализация: ${cap}\n"
        f"Дата выхода на биржу: {date}\n"
        f"Описание: {description}\n\n"
        "Дай краткий инвестиционный анализ этого IPO:\n"
        "- Какие перспективы?\n"
        "- Насколько оно рискованное?\n"
        "- Кому может быть интересно?\n"
        "- Следует ли инвестировать или воздержаться?"
    )
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350
        )
        return response.choices[0].message.content
    except openai.RateLimitError:
        send_to_telegram("⚠️ OpenAI: превышен лимит запросов по IPO. Попробуй позже.")
        return "⚠️ Анализ временно невозможен: превышен лимит OpenAI."
    except Exception as e:
        send_to_telegram(f"❌ Ошибка AI-анализа IPO: {e}")
        return f"❌ Ошибка AI-анализа IPO: {e}"

def run_ipo_monitor():
    ipos = fetch_ipo_data()
    if not ipos:
        send_to_telegram("⚠️ Сегодня нет новых IPO или произошла ошибка при получении данных.")
    else:
        for name, ticker, date, sector, cap, description in ipos:
            analysis = analyze_ipo(name, ticker, date, sector, cap, description)
            msg = (
                f"📈 *{name}* ({ticker})\n"
                f"Сектор: {sector}\n"
                f"Капитализация: ${cap}\n"
                f"Дата IPO: {date}\n"
                f"Описание: {description}\n\n"
                f"*AI-Анализ:*\n{analysis}"
            )
            send_to_telegram(msg)

