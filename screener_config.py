from dataclasses import dataclass, field
from typing import List

@dataclass
class ScreenerConfig:
    price_max: float = 0.10
    market_cap_max: int = 100_000_000
    volume_min: int = 10_000_000
    allowed_platforms: List[str] = field(default_factory=lambda: ["solana", "base", "ethereum", "bsc"])

    min_change_1h_pct: float = 5.0
    min_change_24h_pct: float = 20.0
    min_volume_spike_ratio: float = 2.0

    deep_candidates: int = 30

    enable_telegram_alerts: bool = True
    telegram_bot_token: str = "${TELEGRAM_BOT_TOKEN}"
    telegram_chat_id: str = "${TELEGRAM_CHAT_ID}"

    cron: str = "*/15 * * * *"

    coingecko_api_key: str = "${COINGECKO_API_KEY}"
    coingecko_per_page: int = 250
    coingecko_pages: int = 4

    use_dexscreener: bool = True
