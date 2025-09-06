from dataclasses import dataclass, field
from typing import List

@dataclass
class ScreenerConfig:
    # Базовые фильтры
    price_max: float = 0.10
    market_cap_max: int = 100_000_000  # $100M
    volume_min: int = 10_000_000       # $10M 24h
    allowed_platforms: List[str] = field(default_factory=lambda: ["solana", "base", "ethereum", "bsc"])

    # Импульсные пороги
    min_change_1h_pct: float = 5.0
    min_change_24h_pct: float = 20.0
    min_volume_spike_ratio: float = 2.0  # объём сегодня vs среднее за 7д

    # Кол-во кандидатов на углублённый анализ
    deep_candidates: int = 30

    # Оповещения
    enable_telegram_alerts: bool = True
    telegram_bot_token: str = "${TELEGRAM_BOT_TOKEN}"
    telegram_chat_id: str = "${TELEGRAM_CHAT_ID}"

    # Планировщик
    cron: str = "*/15 * * * *"

    # Ограничения API
    coingecko_api_key: str = "${COINGECKO_API_KEY}"
    coingecko_per_page: int = 250
    coingecko_pages: int = 4

    # Опционально: DexScreener
    use_dexscreener: bool = True
