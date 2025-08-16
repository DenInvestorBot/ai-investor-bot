import httpx, logging
log = logging.getLogger(__name__)
COINGECKO = "https://api.coingecko.com/api/v3"

async def _get_json(url):
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent":"ai-investor-bot/1.0"}) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()

async def collect_new_coins():
    try:
        data = await _get_json(f"{COINGECKO}/search/trending")
        coins = [c['item']['name'] for c in data.get('coins', [])]
        return ", ".join(coins) or "нет данных"
    except Exception:
        log.exception("collect_new_coins failed")
        return "ошибка"
