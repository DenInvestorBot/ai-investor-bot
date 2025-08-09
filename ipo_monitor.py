import os
import datetime
import traceback
import requests
from openai import OpenAI

from crypto_monitor import send_to_telegram, _escape_markdown

print("[ipo_monitor] module loaded")

IPO_API_KEY = os.getenv("IPO_API_KEY")
IPO_API_URL = f"https://financialmodelingprep.com/api/v3/ipo_calendar?apikey={IPO_API_KEY}"

def fetch_real_ipos():
    print("[ipo_monitor] fetching IPO list...")
    today = datetime.date.today()
    try:
        r = requests.get(IPO_API_URL, timeout=20)
        if not r.ok:
            print(f"[ipo_monitor] IPO API response error: {r.status_code}")
            return []
        ipos = r.json() or []
        print(f"[ipo_monitor] received records: {len(ipos)}")
    except Exception:
        print("[ipo_monitor] request to IPO API failed:")
        traceback.print_exc()
        return []

    real_ipos = []
    for ipo in ipos:
        try:
            ipo_date = datetime.datetime.strptime(ipo["date"], "%Y-%m-%d").date()
            if (
                ipo_date <= today
                and ipo.get("exchange") in {"NASDAQ", "NYSE"}
                and ipo.get("price")
                and ipo.get("ticker")
                and ipo.get("companyName")
            ):
                real_ipos.append(ipo)
        except Exception:
            continue

    print(f"[ipo_monitor] valid IPOs after filter: {len(real_ipos)}")
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
        print(f"[ipo_monitor] running AI analysis: {ipo['companyName']} ({ipo['ticker']})")
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
        print("[ipo_monitor] AI analysis failed:")
        traceback.print_exc()
        return "⚠️ AI-анализ недоступен."

def run_ipo_monitor():
    print("[ipo_monitor] start")
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
            print("[ipo_monitor] no IPO found")
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
            print(f"[ipo_monitor] sent: {ipo['companyName']} ({ipo['ticker']})")

        print("[ipo_monitor] done")
    except Exception:
        print("[ipo_monitor] run_ipo_monitor failed:")
        traceback.print_exc()
