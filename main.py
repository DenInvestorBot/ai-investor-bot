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
    val = os.getenv(name)
    if not val:
        log.error("Missing env var %s. Set it in Render → Settings → Environment.", name)
        sys.exit(1)
    return val

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
        from status_check import build_status
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

async def summary_now_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Ручной запуск ежедневной сводки для быстрой проверки
    await job_daily_summary(context.application)
    if update.message:
        await update.message.reply_text("Сводка отправлена (если ADMIN_CHAT_ID задан).")

# -------------------- ДЖОБЫ --------------------
async def job_daily_summary(app: Application) -> None:
    if ADMIN_CHAT_ID is None:
        log.warning("ADMIN_CHAT_ID is not set; skip summary")
        return
    try:
        from reddit_monitor import collect_signals as collect_reddit
        from crypto_monitor import collect_new_coins as collect_coins
        from ipo_monitor import collect_ipos as collect_ipos

        parts = []

        try:
            r = await collect_reddit()
            parts.append(f"Reddit: {r}")
        except Exception:
            log.exception("collect_reddit failed")
            parts.append("Reddit: ошибка")

        try:
            c = await collect_coins()
            parts.append(f"Крипто: {c}")
        except Exception:
            log.exception("collect_new_coins failed")
            parts.append("Крипто: ошибка")

        try:
            i = await collect_ipos()
            parts.append(f"IPO: {i}")
        except Exception:
            log.exception("collect_ipos failed")
            parts.append("IPO: ошибка")

        text = "\n".join(parts) or "Нет свежих данных"
        await app.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Ежедневная сводка\n\n{text}")
    except Exception:
        log.exception("daily_summary failed")

# -------------------- MAIN --------------------
def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Команды
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(CommandHandler("summary_now", summary_now_cmd))

    # Планировщик с устойчивыми настройками
    sch
