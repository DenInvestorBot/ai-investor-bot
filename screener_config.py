# screener_config.py
import os
from typing import List, Optional


class ScreenerConfig:
    """
    Надёжная версия без dataclass:
    - безопасные дефолты
    - автоподхват переменных окружения (токен/чат/ключ)
    - allowed_platforms задаётся через копию списка, чтобы не было мутаций между инстансами
    """

    def __init__(
        self,
        # Базовые фильтры (микрокап + дешёвая цена)
        price_max: float = 0.05,              # ≤ $0.05
        market_cap_max: int = 30_000_000,     # ≤ $30M
        volume_min: int = 2_000_000,          # ≥ $2M/24h
        allowed_platforms: Optional[List[str]] = None,  # по умолчанию ["solana","base","bsc"]

        # Импульсные пороги
        min_change_1h_pct: float = 10.0,      # +10% за 1ч
        min_change_24h_pct: float = 30.0,     # +30% за 24ч
        min_volume_spike_ratio: float = 3.0,  # объём сегодня ≥ 3× среднего за 7д

        # Глубина доп. проверки
        deep_candidates: int = 30,

        # Оповещения
        enable_telegram_alerts: bool = True,
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,

        # Расписание (для информации — планирование задаётся в main.py)
        cron: str = "*/15 * * * *",

        # API параметры
        coingecko_api_key: Optional[str] = None,
        coingecko_per_page: int = 250,
        coingecko_pages: int = 4,

        # DEX горячие токены
        use_dexscreener: bool = True,
    ):
        # Базовые фильтры
        self.price_max = float(price_max)
        self.market_cap_max = int(market_cap_max)
        self.volume_min = int(volume_min)

        if allowed_platforms is None:
            # новый список на каждый инстанс
            self.allowed_platforms = ["solana", "base", "bsc"]
        else:
            self.allowed_platforms = list(allowed_platforms)

        # Импульсные пороги
        self.min_change_1h_pct = float(min_change_1h_pct)
        self.min_change_24h_pct = float(min_change_24h_pct)
        self.min_volume_spike_ratio = float(min_volume_spike_ratio)

        # Доп. проверка
        self.deep_candidates = int(deep_candidates)

        # Оповещения (ENV-алиасы на всякий)
        self.enable_telegram_alerts = bool(enable_telegram_alerts)

        if telegram_bot_token is None:
            telegram_bot_token = (
                os.getenv("TELEGRAM_BOT_TOKEN")
                or os.getenv("BOT_TOKEN")
                or os.getenv("TG_BOT_TOKEN")
                or None
            )
        if telegram_chat_id is None:
            telegram_chat_id = (
                os.getenv("TELEGRAM_CHAT_ID")
                or os.getenv("CHAT_ID")
                or os.getenv("TG_CHAT_ID")
                or None
            )
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id

        # Расписание (информативно)
        self.cron = str(cron)

        # CoinGecko API key (опционально)
        if coingecko_api_key is None:
            coingecko_api_key = os.getenv("COINGECKO_API_KEY")
        self.coingecko_api_key = coingecko_api_key

        # Пагинация CoinGecko
        self.coingecko_per_page = int(coingecko_per_page)
        self.coingecko_pages = int(coingecko_pages)

        # DexScreener
        self.use_dexscreener = bool(use_dexscreener)
