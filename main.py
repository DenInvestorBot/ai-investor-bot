# main.py
import os
import sys
import logging
from typing import List, Optional

from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# -------------------- ЛОГИ --------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("main")

# -------------------- ENV HELPERS --------------------
def get_env_alias(*names: str, required: bool = False) -> Optional[str]:
    """Берём первое непустое значение из списка имён переменных."""
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    if required:
        log.error(
            "Missing env var. Tried: %s. Set one of them in Render → Settings → Environment.",
            ", ".join(names),
        )
        sys.exit(1)
    return None

def get_tz() -> ZoneInfo:
    tz_name = os.getenv("TZ", "Europe/Riga")
    try:
        return ZoneInfo(tz_name)
    except Exception:
        log.warning("Unknown TZ '%s'. Falling back to UTC.", tz_name)
        return ZoneInfo("UTC")

def get_admin_chat_id() -> Optional[int]:
    raw = get_env_alias("ADMIN_CHAT_ID", "CHAT_ID", required=False)
    if not raw:
        log.warning("ADMIN_CHAT_ID/CHAT_ID is not set; daily summary will be skipped.")
        return None
    try:
        return int(raw)
    except ValueError:
        log.error("ADMIN_CHAT_ID/CHAT_ID must be an integer, got %r — summary will be skipped.", raw)
        return None

# -------------------- ENV --------------------
TZ = get_tz()
TELEGRAM_TOKEN = get_env_alias("TELEGRAM_BOT_TOKEN", "BOT_TOKEN", required=True)
ADMIN_CHAT_ID = get_admin_chat_id()

# -------------------- КОМАНДЫ --------------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Привет! Я на связи. Попробуй /status")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text: str
    try:
        from status_check import build_status
        text = await build_status(context)
    except Exception as e:
        log.exception("/status failed, fallback to basic status")
        sched = context.application.bot_data.get("scheduler")
        jobs: List = sched.get_jobs() if sched else []
        lines = [
            "Статус: OK (fallback)",
