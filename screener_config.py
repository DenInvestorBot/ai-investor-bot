from dataclasses import dataclass, field
from typing import List

@dataclass
class ScreenerConfig:
    # --- Базовые фильтры (микрокап + дешёвая цена) ---
    price_max: float = 0.05            # ≤ $0.05 за монету
    market_cap_max: int = 30_000_000   # ≤ $30M капа
    volume_min: int = 2_000_000        # ≥ $2M объём 24ч
    allowed_platforms: List[str] = field(
        default_factory=lambda: ["solana", "base", "bsc"]  # целимся в сети с «раскочегариванием»
    )

    # --- Импульсные пороги (ловим разгон) ---
    min_change_1h_pct: float = 10.0    # +10% за 1ч
    min_change_24h_pct: float = 30.0   # +30% за 24ч
    min_volume_spike_ratio: float = 3.0  # объём сегодня ≥ 3× среднего за 7д

    # --- Сколько монет углублённо проверять графиком объёма ---
    deep_candidates: int = 30

    # --- Оповещения в Telegram ---
    enable_telegram_alerts: bool = True
    telegram_bot_token: str = "${TELEGRAM_BOT_TOKEN}"  # или BOT_TOKEN/TG_BOT_TOKEN на уровне кода
    telegram_chat_id: str = "${TELEGRAM_CHAT_ID}"

    # --- Расписание ---
    cron: str = "*/15 * * * *"  # каждые 15 минут

    # --- Ограничения/параметры API ---
    coingecko_api_key: str = "${COINGECKO_API_KEY}"  # можно пусто
    coingecko_per_page: int = 250
    coingecko_pages: int = 4   # до ~1000 монет за проход

    # --- DEX горячие токены (DexScreener) ---
    use_dexscreener: bool = True
