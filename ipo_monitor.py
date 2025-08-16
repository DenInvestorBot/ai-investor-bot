import logging
log = logging.getLogger(__name__)

async def collect_ipos():
    try:
        # Заглушка: подключите ваш источник NASDAQ/альтернативный API
        return "нет новых IPO"
    except Exception:
        log.exception("collect_ipos failed")
        return "ошибка"
