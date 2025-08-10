# main.py — безопасная версия (UTF-8, без эмодзи)
from __future__ import annotations
import asyncio
import os
import logging
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from scheduler.advisor_scheduler import register_advisor_jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("boot")

def safe_import(name: str):
    try:
        module = __import__(name)
        log.info("[%s] module loaded", name)
        return module
    except Exception as e:
        log.warning("[%s] not loaded: %s", name, e)
        return None

# Загружаем твои модули (если есть)
crypto_monitor = safe_import("crypto_monitor")
ipo_monitor    = safe_import("ipo_monitor")
reddit_monitor = safe_import("reddit_monitor")
status_check   = safe_import("status_check")

RIGA_TZ = ZoneInfo("Europe/Riga")

async def main():
    log.info("Init bot...")

    # 1) Планировщик
    scheduler = AsyncIOScheduler(timezone=RIGA_TZ)

    # 2) Советник TSLA/GME (дневки) — 23:10 Europe/Riga, пн–пт
    register_advisor_jobs(scheduler, hour=23, minute=10)
    log.info("[advisor] TSLA/GME daily advisor scheduled at 23:10 Europe/Riga")

    # 3) Если модули имеют register_jobs(scheduler) — подключим их задачи
    for m in (crypto_monitor, ipo_monitor, reddit_monitor, status_check):
        if m and hasattr(m, "register_jobs"):
            try:
                m.register_jobs(scheduler)
                log.info("[%s] jobs registered", m.__name__)
            except Exception as e:
                log.warning("[%s] register_jobs failed: %s", m.__name__, e)

    # 4) Старт планировщика
    scheduler.start()
    log.info("Scheduler started (tz=Europe/Riga)")

    # 5) Одноразовый тест советника при старте (по желанию)
    if os.getenv("ADVISOR_BOOT_ONCE") == "1":
        try:
            from bot.advisor_jobs import run_tsla_gme_daily_job
            run_tsla_gme_daily_job()
            log.info("[advisor] boot test sent")
        except Exception as e:
            log.warning("[advisor] boot test failed: %s", e)

    # держим процесс живым
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutdown")
