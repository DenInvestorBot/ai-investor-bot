import os, asyncio, logging
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application, CommandHandler

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("main")

TZ = ZoneInfo("Europe/Riga")

async def start_cmd(update, context):
    await update.message.reply_text("Привет! Я на связи. Попробуй /status")

async def status_cmd(update, context):
    try:
        from status_check import build_status
        text = await build_status(context)
    except Exception as e:
        log.exception("/status failed")
        text = f"Статус: ERROR — {e}"
    await update.message.reply_text(text)

async def job_daily_summary(app):
    chat_id = os.getenv('ADMIN_CHAT_ID')
    if not chat_id:
        log.warning("ADMIN_CHAT_ID is not set; skip summary")
        return
    try:
        from reddit_monitor import collect_signals as collect_reddit
        from crypto_monitor import collect_new_coins as collect_coins
        from ipo_monitor import collect_ipos as collect_ipos

        parts = []
        r = await collect_reddit()
        parts.append(f"Reddit: {r}")
        c = await collect_coins()
        parts.append(f"Крипто: {c}")
        i = await collect_ipos()
        parts.append(f"IPO: {i}")

        text = "\n".join(parts) or "Нет свежих данных"
        await app.bot.send_message(chat_id=int(chat_id), text=f"Ежедневная сводка\n\n{text}")
    except Exception:
        log.exception("daily_summary failed")

async def main():
    token = os.environ['TELEGRAM_BOT_TOKEN']
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("status", status_cmd))

    scheduler = AsyncIOScheduler(timezone=TZ)
    scheduler.add_job(lambda: asyncio.create_task(job_daily_summary(application)),
                      trigger='cron', hour=21, minute=0, id='daily_summary')
    scheduler.start()
    application.bot_data['scheduler'] = scheduler

    log.info("Starting bot (long polling)... TZ=Europe/Riga")
    await application.initialize()
    await application.start()
    try:
        await application.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
