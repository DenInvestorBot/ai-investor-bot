import os
import datetime
import traceback
import requests
from openai import OpenAI

from crypto_monitor import send_to_telegram, _escape_markdown

print("📄 [ipo_monitor] Модуль загружен")

IPO_API_KEY = os.getenv("IPO_API_KEY")
IPO_API_URL = f"https://financialmodelingprep.com/api/v3/ipo_calendar?apikey={IPO_API_KEY}"

def fetch_real_ipos():
    print("🔎 [ipo_monitor] Запрос списка IPO...")
    today = datetime.date.today()
    try:
        r = requests.get(IPO_API_URL, timeout=20)
        if not r.ok:
            print(f"⚠️ [ipo_monitor] Ошибка ответа API IPO: {r.status_code}")
            return []
        ipos = r.json() or []
        print(f"✅ [ipo_monitor] Получено записей: {len(ipos)}")
    except Exception:
        print("❌ [ipo_monitor] Сбой при запросе IPO:")
        traceback.print_exc()
        return []

    real_ipos = []
    for ipo in ipos:
        try:
            ipo_date = datetime.datetime.strptime(ipo["date"], "%Y-%m-%d").date()
            if (
                ipo_date <= today and
                ipo.get("exchange") in {"NASDAQ", "NYSE"} and
                ipo.get("price") and
                ipo.get("ticker") and
                ipo.get("companyName")
            ):
                real_ipos.append(ipo)
        except Exception:
            # пропускаем битые записи, логировать не обязательно
            continue

    print(f"📊 [ipo_monitor] Отфильтровано валидных IPO: {len(real_ipos)}")
    return real_ipos

def analyze_ipo(ipo, client: OpenAI):
    prompt = (
        "Ты финансовый аналитик. Сформируй короткий аналитический вывод по IPO.\n"
        "Максимум 6 сжатых пунктов. Отдельно отметь ключевые риски.\n\n"
        f"Компания: {ipo['companyName']}\n"
        f"Тикер: {ipo['ticker']}\n"
        f"Сектор: {ipo.get('sector', 'не указан')}\n"
        f"Цена размещения: {ipo.get('price', 'не указана')}\n"
    )
    try:
        print(f"🤖 [ipo_monitor] AI-анализ IPO: {ipo['companyName']} ({ipo['ticker']})")
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты финансовый аналитик."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=350,
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        print("❌ [ipo_monitor] Ошибка AI при анализе IPO:")
        traceback.print_exc()
        return "⚠️ AI-анализ недоступен."

def run_ipo_monitor():
    print("🚀 [ipo_monitor] Запуск мониторинга IPO...")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        msg = "❌ Не задан OPENAI_API_KEY"
        print(f"[ipo_monitor] {msg}")
        send_to_telegram(_escape_markdown(msg))
        return

    client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        ipos = fetch_real_ipos()
        if not ipos:
            send_to_telegram(_escape_markdown("Сегодня не было новых IPO на бирже."))
            print("ℹ️ [ipo_monitor] Нет подходящих IPO")
            return

        for ipo in ipos:
            header = (
                f"📈 {ipo['companyName']} ({ipo['ticker']})\n"
                f"Дата IPO: {ipo['date']}\n"
                f"Биржа: {ipo['exchange']}\n"
                f"Цена размещения: {ipo['price']}\n"
                f"Сектор: {ipo.get('sector', 'не указан')}\n\n"
            )
            analysis = analyze_ipo(ipo, client)
            msg = header + analysis
            send_to_telegram(_escape_markdown(msg))
            print(f"📨 [ipo_monitor] Сообщение отправлено: {ipo['companyName']} ({ipo['ticker']})")
        print("✅ [ipo_monitor] Мониторинг IPO завершён")
    except Exception:
        print("❌ [ipo_monitor] Ошибка в run_ipo_monitor:")
        traceback.print_exc()
