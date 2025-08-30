# main.py
# -*- coding: utf-8 -*-
import os
import asyncio
import datetime as dt
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)

from ai_crypto_report import generate_ai_crypto_report

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))  # можно оставить пустым и взять из /ping позже
LOCAL_TZ = ZoneInfo("Europe/Riga")

# --- утилита: безопасная отправка длинных сообщений (лимит Telegram ~4096) ---
def split_chunks(text: str, limit: int = 3900):
    part = []
    count = 0
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

# --- команды ---
async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"pong ✅\n`chat_id` = {chat_id}", parse_mode="Markdown")

async def cmd_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        md = generate_ai_crypto_report(vs_currency="usd", model="gpt-4.1")
        await send_markdown(context.bot, update.effective_chat.id, md)
    except Exception as e:
        await update.message.reply_text(f"❗️Ошибка генерации отчёта: {e}")

# --- ежедневная задача через JobQueue ---
async def job_daily_report(context: ContextTypes.DEFAULT_TYPE):
    try:
        target_chat = CHAT_ID or int(os.getenv("TELEGRAM_CHAT_ID", "0")) or None
        if not target_chat:
            # если не задан chat_id — пропускаем тихо
            return
        md = generate_ai_crypto_report(vs_currency="usd", model="gpt-4.1")
        await send_markdown(context.bot, target_chat, md)
    except Exception as e:
        if target_chat:
            await context.bot.send_message(target_chat, f"❗️Ошибка генерации отчёта: {e}")

async def on_startup(app):
    # на всякий — выключим вебхук, чтобы не конфликтовал с polling
    await app.bot.delete_webhook(drop_pending_updates=True)

    # планируем ежедневную задачу
    run_time = dt.time(hour=21, minute=0, tzinfo=LOCAL_TZ)
    app.job_queue.run_daily(
        job_daily_report,
        time=run_time,
        name="daily_crypto_report",
    )

def main():
    if not BOT_TOKEN:
        raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN")

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()

    # команды
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("now", cmd_now))

    # старт бота (polling + JobQueue внутри)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
