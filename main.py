# main.py
# -*- coding: utf-8 -*-
import os
import asyncio
import datetime as dt
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from ai_crypto_report import generate_ai_crypto_report

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
        fp = os.getenv(f"{key}_FILE", "")
        if fp and os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return content
            except Exception:
                pass
    return ""

def read_token() -> str:
    return read_secret_var("TELEGRAM_BOT_TOKEN", "BOT_TOKEN", "TOKEN")

def read_chat_id() -> str:
    return os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "")).strip()

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
        await bot.send_message(chat_id=chat_id, text=chunk, parse_mode="Markdown")

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

# ---------- Ежедневная рассылка: два варианта ----------
async def job_daily_report(context: ContextTypes.DEFAULT_TYPE):
    try:
        cid_raw = read_chat_id()
        target_chat = int(cid_raw) if cid_raw.lstrip("-").isdigit() else None
        if not target_chat:
            return
        md = generate_ai_crypto_report(vs_currency="usd", model="gpt-4.1")
        await send_markdown(context.bot, target_chat, md)
    except Exception as e:
        if target_chat:
            await context.bot.send_message(target_chat, f"❗️Ошибка генерации отчёта: {e}")

async def daily_loop(app):
    """Fallback-планировщик на asyncio, если JobQueue недоступен."""
    while True:
        now = dt.datetime.now(LOCAL_TZ)
        target = now.replace(hour=21, minute=0, second=0, microsecond=0)
        if target <= now:
            target += dt.timedelta(days=1)
        wait_sec = (target - now).total_seconds()
        await asyncio.sleep(wait_sec)
        try:
            cid_raw = read_chat_id()
            target_chat = int(cid_raw) if cid_raw.lstrip("-").isdigit() else None
            if not target_chat:
                continue
            md = generate_ai_crypto_report(vs_currency="usd", model="gpt-4.1")
            await send_markdown(app.bot, target_chat, md)
        except Exception as e:
            # логируем, но не падаем
            print("daily_loop error:", e)
            await asyncio.sleep(5)

async def on_startup(app):
    await app.bot.delete_webhook(drop_pending_updates=True)

    # Пытаемся использовать JobQueue, если установлен extra-модуль
    if getattr(app, "job_queue", None) is not None:
        run_time = dt.time(hour=21, minute=0, tzinfo=LOCAL_TZ)
        app.job_queue.run_daily(job_daily_report, time=run_time, name="daily_crypto_report")
        print("JobQueue: план на 21:00 (Europe/Riga) установлен")
    else:
        # Fallback на чистый asyncio
        asyncio.create_task(daily_loop(app))
        print("JobQueue недоступен — запущен fallback-планировщик (asyncio).")

    # Лог конфигурации
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
    app.add_handler(CommandHandler("ping", cmd_ping"))
    app.add_handler(CommandHandler("now", cmd_now))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
