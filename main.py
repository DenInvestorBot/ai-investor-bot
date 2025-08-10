# main.py
# Универсальный запуск твоего бота на Render + ежедневный советник TSLA/GME
from __future__ import annotations
import asyncio
import os
import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- ЛОГИ ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("boot")

# --- СЮДА ПОДКЛЮЧАЕМ НАШ СОВЕТНИК ---
from scheduler.advisor_scheduler import register_advisor_jobs

# --- Импорт твоих модулей (как раньше). Они либо сами что-то планируют,
#     либо мы просто хотим, чтобы они подгрузились и были готовы.
def safe_import(name: str):
    try:
        module = __import__(name)
        log.info("[%s] module loaded", name)
        return module
    except Exception as e:
        log.warning("[%s] not loaded: %s", name, e)
        return None

crypto_monitor = safe_import("crypto_monitor")
ipo_monitor    = safe_import("ipo_monitor")
reddit_monitor = safe_import("reddit_monitor")
status_check   = safe_import("status_check")  # если у тебя там ежедневная сводка и т.п.

RIGA_TZ = ZoneInfo("Europe/Riga")

async def main():
    log.info("🚀 Инициализация бота...")

    # 1) Планировщик
    scheduler = AsyncIOScheduler(timezone=RIGA_TZ)

    # 2) Регистрируем ежедневный советник TSLA/GME (дневки, пн–пт, 23:10 по Риге)
    register_advisor_jobs(scheduler, hour=23, minute=10)
    log.info("[advisor] TSLA/GME daily advisor scheduled at 23:10 Europe/Riga")

    # 3) Если какие-то из твоих модулей имеют функцию register_jobs(scheduler) — вызовем её
    for m in (crypto_monitor, ipo_monitor, reddit_monitor, status_check):
        if m and hasattr(m, "register_jobs"):
            try:
                m.register_jobs(scheduler)
                log.info("[%-15s] jobs registered", m.__name__)
            except Exception as e:
                log.warning("[%-15s] register_jobs failed: %s", m.__name__, e)

    # 4) Старт
    scheduler.start()
    log.info("✅ План
