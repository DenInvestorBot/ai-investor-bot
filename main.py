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

# -------------------- ENV & TZ --------------------
def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        log.error("Missing env var %s. Set it in Render → Settings → Environment.", name)
        sys.exit(1)
    return value

def get_tz() -> ZoneInfo:
    tz_name = os.getenv("TZ", "Europe/Riga")
    try:
        return ZoneInfo(tz_name)
    except Exception:
        log.warning("Unknown TZ '%s'. Falling back to UTC.", tz_name)
        return ZoneInfo("UTC")

def get_admin_chat_id() -> Optional[int]:
    raw = os.getenv("ADMIN_CHAT_ID")
    if not raw:
        log.warning("ADMIN_CHAT_ID is not set; daily summary will be skipped.")
        return None
    try:
        return int(raw)
    except ValueError:
        log.error("ADMIN_CHAT_ID must be an integer, got %r — summary will be skipped.", raw)
        return None

TZ = get_tz()
TELEGRAM_TOKEN = require_env("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = get_admin_chat_id()

# -------------------- КОМАНДЫ --------------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Привет! Я на связи. Попробуй /status")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text: str
    try:
        from status_check import build_status  # твой файл
        text = await build_status(context)
    except Exception as e:
        log.exception("/status failed, fallback to basic status")
        sched = context.application.bot_data.get("scheduler")
        jobs: List = sched.get_jobs() if sched else []
        lines = [
            "Статус: OK (fallback)",
            f"TZ: {TZ}",
            f"Активных задач: {len(jobs)}",
            f"ADMIN_CHAT_ID set: {'yes' if ADMIN_CHAT_ID is not None else 'no'}",
            f"Ошибка build_status: {e.__class__.__name__}",
        ]
        for j in jobs:
            lines.append(f"• {j.id}: next={j.next_run_time}")
        text = "\n".join(lines)
    if update.message:
        await update.message.reply_text(text)

async def summary_now_cmd
