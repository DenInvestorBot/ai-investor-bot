import os
import datetime as dt
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)

from ai_crypto_report import generate_ai_crypto_report

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
LOCAL_TZ = ZoneInfo("Europe/Riga")

# --- Команды ---
async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"pong ✅\n`chat_id` = {chat_id}", parse_mode="Markdown")

async def cmd_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        md = generate_ai_crypto_report(vs_currency="usd", model="gpt-4.1")
        # если хочешь — можно распилить на два сообщения, если слишком длинно
        await update.message.reply_text(md, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❗️Ошибка генерации отчёта: {e}")

# --- Ежедневная задача через JobQueue ---
async def send_daily_report(context: ContextTypes.DEFAULT_TYPE):
    try:
        md = generate_ai_crypto_report(vs_currency="usd", model="gpt-4.1")
        await context.bot.send_message(chat_id=CHAT_ID or context.job.chat_id, text=md, parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(chat_id=CHAT_ID or context.job.chat_id, text=f"❗️Ошибка генерации отчёта: {e}")

async def on_startup(app):
    # На всякий: выключим вебхук, чтобы не конфликтовал с polling
    await app.bot.delete_webhook(drop_pending_updates=True)

    # План: 21:00 по Риге, каждый день
    run_time = dt.time(hour=21, minute=0, tzinfo=LOCAL_TZ)
    app.job_queue.run_daily(
        send_daily_report,
        time=run_time,
        name="daily_crypto_report",
        chat_id=CHAT_ID if CHAT_ID else None,  # можно оставить None и брать из контекста
    )

def main():
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()

    # Команды
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("now", cmd_now))

    # Запуск (поллинг + JobQueue внутри)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
