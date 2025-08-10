# scheduler/advisor_scheduler.py
from __future__ import annotations
from zoneinfo import ZoneInfo
from apscheduler.triggers.cron import CronTrigger

from bot.advisor_jobs import run_tsla_gme_daily_job

RIGA_TZ = ZoneInfo("Europe/Riga")

# Default time: 23:10 Europe/Riga (after US market close in summer; safe buffer)
DEFAULT_HOUR = 23
DEFAULT_MINUTE = 10

def register_advisor_jobs(scheduler, hour: int = DEFAULT_HOUR, minute: int = DEFAULT_MINUTE):
    """Attach daily advisor job for TSLA & GME to the given APScheduler instance."""
    trigger = CronTrigger(day_of_week='mon-fri', hour=hour, minute=minute, timezone=RIGA_TZ)
    scheduler.add_job(run_tsla_gme_daily_job, trigger, id="advisor.daily.tsla_gme", replace_existing=True)
