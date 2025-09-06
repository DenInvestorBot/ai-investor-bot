import os
from typing import List, Optional

class ScreenerConfig:
    def __init__(
        self,
        price_max: float = 0.05,
        market_cap_max: int = 30_000_000,
        volume_min: int = 2_000_000,
        allowed_platforms: Optional[List[str]] = None,
        min_change_1h_pct: float = 10.0,
        min_change_24h_pct: float = 30.0,
        min_volume_spike_ratio: float = 3.0,
        deep_candidates: int = 30,
        enable_telegram_alerts: bool = True,
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        cron: str = "*/15 * * * *",
        coingecko_api_key: Optional[str] = None,
        coingecko_per_page: int = 250,
        coingecko_pages: int = 4,
        use_dexscreener: bool = True,
    ):
        self.price_max = float(price_max)
        self.market_cap_max = int(market_cap_max)
        self.volume_min = int(volume_min)
        self.allowed_platforms = list(allowed_platforms) if allowed_platforms else ["solana", "base", "bsc"]
        self.min_change_1h_pct = float(min_change_1h_pct)
        self.min_change_24h_pct = float(min_change_24h_pct)
        self.min_volume_spike_ratio = float(min_volume_spike_ratio)
        self.deep_candidates = int(deep_candidates)
        self.enable_telegram_alerts = bool(enable_telegram_alerts)
        if telegram_bot_token is None:
            telegram_bot_token = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TG_BOT_TOKEN") or None)
        if telegram_chat_id is None:
            telegram_chat_id = (os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or os.getenv("TG_CHAT_ID") or None)
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.cron = str(cron)
        if coingecko_api_key is None:
            coingecko_api_key = os.getenv("COINGECKO_API_KEY")
        self.coingecko_api_key = coingecko_api_key
        self.coingecko_per_page = int(coingecko_per_page)
        self.coingecko_pages = int(coingecko_pages)
        self.use_dexscreener = bool(use_dexscreener)
