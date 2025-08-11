from __future__ import annotations
from zoneinfo import ZoneInfo
from apscheduler.triggers.cron import CronTrigger
from bot.advisor_jobs import run_tsla_gme_daily_job
import traceback

print("📄 [advisor_scheduler] Модуль загружен")

RIGA_TZ = ZoneInfo("Europe/Riga")
DEFAULT_HOUR = 23
DEFAULT_MINUTE = 10  # после закрытия рынка США (с запасом)

def register_advisor_jobs(scheduler, hour: int = DEFAULT_HOUR, minute: int = DEFAULT_MINUTE):
    """
    Добавляет ежедневное задание советника (TSLA и GME) в планировщик.
    """
    try:
        trigger = CronTrigger(
            day_of_week="mon-fri",
            hour=hour,
            minute=minute,
            timezone=RIGA_TZ
        )
        scheduler.add_job(
            run_tsla_gme_daily_job,
            trigger,
            id="advisor.daily.tsla_gme",
            replace_existing=True
        )
        print(f"✅ [advisor_scheduler] Задача советника зарегистрирована на {hour:02d}:{minute:02d} (Europe/Riga)")
    except Exception:
        print("❌ [advisor_scheduler] Ошибка при регистрации задачи советника:")
        traceback.print_exc()
