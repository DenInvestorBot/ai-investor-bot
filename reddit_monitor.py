import logging, httpx

log = logging.getLogger(__name__)
UA = {"User-Agent":"ai-investor-bot/1.0"}
TICKERS = ["GME", "RBNE"]

async def _search_reddit(q: str):
    url = f"https://www.reddit.com/search.json?q={q}&sort=new&restrict_sr=0&t=day"
    async with httpx.AsyncClient(timeout=20, headers=UA) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
        return [i['data']['title'] for i in data.get('data',{}).get('children', [])][:5]

async def collect_signals():
    try:
        out = []
        for t in TICKERS:
            posts = await _search_reddit(t)
            if posts:
                out.append(f"{t}: {len(posts)} упоминаний (напр.: {posts[0][:80]}…)")
            else:
                out.append(f"{t}: нет свежих сигналов")
        return " | ".join(out)
    except Exception:
        log.exception("collect_signals failed")
        return "ошибка"
