# -*- coding: utf-8 -*-
import os
import asyncio
import datetime as dt
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from ai_crypto_report import generate_ai_crypto_report, diagnose_sources
from crypto_monitor import collect_new_coins
from reddit_monitor import collect_signals
from ipo_monitor import collect_ipos
from status_check import build_status

LOCAL_TZ = ZoneInfo("Europe/Riga")

# ---------- Утилиты ----------
def mask(s: str, keep: int = 6) -> str:
    if not s:
        return "(empty)"
    if len(s) <= keep:
        return "*" * len(s)
    return s[:keep] + "..." + "*" * 4

def read_secret_var(*keys: str) -> str:
    for key in keys:
        val = os.getenv(key, "")
        if val:
            return val.strip()
        fpath = os.getenv(f"{key}_FILE", "")
        if fpath and os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return content
            except Exception:
                pass
    return ""

def read_token() -> str:
    return read_secret_var("TELEGRAM_BOT_TOKEN", "BOT_TOKEN", "TOKEN")

def read_chat_id() -> str:
    return (
        os.getenv("TELEGRAM_CHAT_ID")
        or os.getenv("ADMIN_CHAT_ID")
        or os.getenv("CHAT_ID", "")
    ).strip()

def read_openai_key() -> str:
    return read_secret_var("OPENAI_API_KEY")

def split_chunks(text: str, limit: int = 3900):
    part, count = [], 0
    for line in text.splitlines(keepends=True):
        if count + len(line) > limit:
            yield "".join(part)
            part, count = [line], len(line)
        else:
            part.append(line); count += len(line)
    if part:
        yield "".join(part)

async def send_markdown(bot, chat_id: int, text: str):
    for chunk in split_chunks(text):
        await bot.send_message(chat_id=chat_id, text=chunk, parse_mode=ParseMode.HTML)

# ---------- Команды ----------
async def cmd_env(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bt = read_token()
    cid = read_chat_id()
    ok = read_openai_key()
    files = ", ".join(sorted(os.listdir(".")))
    msg = (
        "🔧 ENV на рантайме:\n"
        f"• TELEGRAM_BOT_TOKEN = {mask(bt)}\n"
        f"• TELEGRAM_CHAT_ID   = {cid or '(empty)'}\n"
        f"• OPENAI_API_KEY     = {mask(ok)}\n"
        f"• CWD                = {os.getcwd()}\n"
        f"• FILES              = {files}\n"
    )
    await update.message.reply_text(msg)

async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"pong ✅\n`chat_id` = {update.effective_chat.id}", parse_mode="Markdown")

async def cmd_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        md = generate_ai_crypto_report(vs_currency="usd", model="gpt-4.1")
        await send_markdown(context.bot, update.effective_chat.id, md)
    except Exception as e:
        await update.message.reply_text(f"❗️Ошибка генерации отчёта: {e}")

async def cmd_diag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        diag = diagnose_sources()
    except Exception as e:
        diag = f"Ошибка диагностики: {e}"
    await update.message.reply_text("🔍 Диагностика:\n" + diag)

# ---------- Краткая сводка + AI-отчёт ----------
async def build_summary() -> str:
    parts = ["<b>📊 Краткая сводка</b>"]
    try:
        parts.append("• Тренды: " + await collect_new_coins())
    except Exception:
        parts.append("• Тренды: ошибка")
    try:
        parts.append("• Reddit: " + await collect_signals())
    except Exception:
        parts.append("• Reddit: ошибка")
    try:
        parts.append("• IPO: " + await collect_ipos())
    except Exception:
        parts.append("• IPO: ошибка")
    parts.append("")
    parts.append(generate_ai_crypto_report(vs_currency="usd", model="gpt-4.1"))
    return "\n".join(parts)

async def cmd_summary_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        txt = await build_summary()
        await send_markdown(context.bot, update.effective_chat.id, txt)
    except Exception as e:
        await update.message.reply_text(f"❗️Ошибка сводки: {e}")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = await build_status(context)
    except Exception as e:
        text = f"Ошибка статуса: {e}"
    await update.message.reply_text(text)

# ---------- Ежедневная рассылка ----------
async def job_daily_report(context: ContextTypes.DEFAULT_TYPE):
    try:
        cid_raw = read_chat_id()
        target_chat = int(cid_raw) if cid_raw.lstrip("-").isdigit() else None
        if not target_chat:
            return
        txt = await build_summary()
        await send_markdown(context.bot, target_chat, txt)
    except Exception as e:
        if 'target_chat' in locals() and target_chat:
            await context.bot.send_message(target_chat, f"❗️Ошибка генерации сводки: {e}")

async def daily_loop(app):
    while True:
        now = dt.datetime.now(LOCAL_TZ)
        target = now.replace(hour=21, minute=0, second=0, microsecond=0)
        if target <= now:
            target += dt.timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            cid_raw = read_chat_id()
            target_chat = int(cid_raw) if cid_raw.lstrip("-").isdigit() else None
            if not target_chat:
                continue
            txt = await build_summary()
            await send_markdown(app.bot, target_chat, txt)
        except Exception as e:
            print("daily_loop error:", e)
            await asyncio.sleep(5)

# ---------- Старт ----------
async def on_startup(app):
    await app.bot.delete_webhook(drop_pending_updates=True)

    if getattr(app, "job_queue", None) is not None:
        run_time = dt.time(hour=21, minute=0, tzinfo=LOCAL_TZ)
        app.job_queue.run_daily(job_daily_report, time=run_time, name="daily_crypto_report")
        app.bot_data["scheduler"] = app.job_queue.scheduler
        print("JobQueue: расписание на 21:00 (Europe/Riga) установлено")
    else:
        asyncio.create_task(daily_loop(app))
        print("JobQueue недоступен — запущен fallback-планировщик (asyncio)")

    print("=== STARTUP CONFIG ===")
    print("TELEGRAM_BOT_TOKEN =", mask(read_token()))
    print("TELEGRAM_CHAT_ID   =", read_chat_id() or "(empty)")
    print("OPENAI_API_KEY     =", mask(read_openai_key()))
    print("CWD =", os.getcwd())
    print("FILES =", os.listdir("."))
    print("======================")

def main():
    token = read_token()
    if not token:
        print("❌ Не найден TELEGRAM_BOT_TOKEN/BOT_TOKEN/TOKEN (или *_FILE). Проверь ENV на Render.")
        raise SystemExit(1)

    app = ApplicationBuilder().token(token).post_init(on_startup).build()
    app.add_handler(CommandHandler("env", cmd_env))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("now", cmd_now))
    app.add_handler(CommandHandler("diag", cmd_diag))
    app.add_handler(CommandHandler("summary_now", cmd_summary_now))
    app.add_handler(CommandHandler("status", cmd_status))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
