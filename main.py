import openai
import asyncio, time, requests, feedparser
from telegram import Bot
from bs4 import BeautifulSoup
from datetime import datetime
import os

bot = Bot(token=os.environ['BOT_TOKEN'])
chat_id = os.environ['CHAT_ID']
openai.api_key = os.environ['OPENAI_API_KEY']

# --- Крипта ---
def get_new_coins():
    url = "https://api.coingecko.com/api/v3/coins/list"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else []

def analyze_coin(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    r = requests.get(url)
    if r.status_code != 200: return "⚠️ Не удалось получить данные"
    d = r.json()
    name, symbol = d['name'], d['symbol']
    cap = d.get('market_data', {}).get('market_cap', {}).get('usd', 0)
    vol = d.get('market_data', {}).get('total_volume', {}).get('usd', 0)
    score = vol / cap if cap else 0
    tone = "📈 Объём нормальный." if score < 1 else "⚠️ Объём подозрительно высок."
    risk = "🟢 Перспективно" if cap > 10_000_000 else "⚠️ Высокий риск"
    return f"🚀 {name} ({symbol.upper()})\n💰 Капа: ${cap}\n📊 Объём: ${vol}\n{tone}\n{risk}"

# --- IPO ---
def get_ipos():
    html = requests.get("https://www.nasdaq.com/market-activity/ipos", headers={"User-Agent": "Mozilla"}).text
    soup = BeautifulSoup(html, 'lxml')
    rows = soup.find_all("tr")[1:]
    ipos = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 5:
            ipos.append(f"📢 IPO: {cols[1].text.strip()} ({cols[0].text.strip()})\n📆 {cols[2].text.strip()} | 💵 {cols[4].text.strip()}")
    return ipos

# --- Reddit ---
tickers = ['GME', 'RBNE', 'TSLA', 'AAPL', 'META', 'AMZN', 'MSFT', 'NVDA', 'GOOGL', 'NFLX']
last_titles = set()

def check_reddit():
    feed = feedparser.parse('https://www.reddit.com/r/stocks/.rss')
    found = []
    for entry in feed.entries:
        title = entry.title
        if title in last_titles:
            continue
        for t in tickers:
            if t in title:
                found.append((t, title))
                last_titles.add(title)
    return found

def gpt_summary(text):
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Определи, что происходит в посте: '{text}' — паника, нейтрально или позитивно. Сформулируй кратко."}]
        )
        return res.choices[0].message['content']
    except:
        return "(GPT ошибка)"

# --- Асинхронный запуск ---
async def run():
    global last_titles
    known_coins = set(c['id'] for c in get_new_coins())
    while True:
        try:
            coins = get_new_coins()
            for coin in coins:
                if coin['id'] not in known_coins:
                    msg = analyze_coin(coin['id'])
                    await bot.send_message(chat_id, msg)
                    known_coins.add(coin['id'])

            ipos = get_ipos()
            for ipo in ipos:
                await bot.send_message(chat_id, ipo)

            posts = check_reddit()
            for t, title in posts:
                summary = gpt_summary(title)
                await bot.send_message(chat_id, f"🧵 {t}: {title}\n🧠 GPT: {summary}")

            now = datetime.now()
            if now.hour == 21 and now.minute < 10:
                await bot.send_message(chat_id, "🕘 Вечерняя сводка будет позже!")

            await asyncio.sleep(3600)
        except Exception as e:
            print("Ошибка:", e)
            await asyncio.sleep(120)

asyncio.run(run())
