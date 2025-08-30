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
    """
    Возвращает значение из первого найденного:
    - ENV по ключу
    - ENV по ключу с суффиксом _FILE (читаем содержимое файла)
    Пример: TELEGRAM_BOT_TOKEN или TELEGRAM_BOT_TOKEN_FILE=/opt/secret/token
    """
    for key in keys:
        val = os.getenv(key, "")
        if val:
            return val.strip()
        file_path = os.getenv(f"{key}_FILE", "")
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return content
            except Exception:
                pass
    return ""

def read_token() -> str:
    # Поддерживаем разные варианты имён, чтобы ничего не «сломалось»
    return read_secret_var(
        "TELEGRAM_BOT_TOKEN", "BOT_TOKEN", "TOKEN"
    )

def read_chat_id() -> str:
    return os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", "")).strip()

def read_openai_key() -> str:
    return read_secret_var("OPENAI_API_KEY")

# разовый снапшот ENV
BOT_TOKEN = read_token()
CHAT_ID_RAW = read_chat_id()
OPENAI_KEY = read_openai_key()
CHAT_ID = int(CHAT_ID_RAW) if CHAT_ID_RAW.lstrip("-").isdigit() else 0

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

# ---------- Команды ----------
async def cmd_env(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # перечитываем на случай изменений в рантайме
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

as
