# status_check.py
import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

def _get_tz() -> ZoneInfo:
    name = os.getenv("TZ", "Europe/Riga")
    try:
        return ZoneInfo(name)
    except Exception:
        log.warning("Unknown TZ '%s'. Falling back to UTC.", name)
        return ZoneInfo("UTC")

TZ = _get_tz()

def _admin_status() -> str:
    raw = os.getenv("ADMIN_CHAT_ID") or os.getenv("CHAT_ID")
    if not raw:
        return "no"
    try:
        int(raw)
        return "yes"
    except ValueError:
        return f"invalid ({raw!r})"

async def build_status(context) -> str:
    lines = []

    try:
        me = await context.bot.get_me()
        lines.append(f"Бот: @{getattr(me, 'username', None) or 'unknown'} ({me.id})")
    except Exception:
        log.exception("get_me failed")
        lines.append("Бот: <не удалось получить getMe()>")

    now_tz = datetime.now(tz=TZ)
    lines.append(f"Серверное время: {now_tz:%Y-%m-%d %H:%M:%S %Z}")

    sched = context.application.bot_data.get("scheduler")
    if not sched:
        lines += [
            "Планировщик: не инициализирован",
            f"TZ: {TZ}",
            f"ADMIN_CHAT_ID set: {_admin_status()}",
            "Подсказка: /summary_now — отправить сводку вручную.",
        ]
        return "\n".join(lines)

    jobs = sched.get_jobs() or []
    lines.append(f"Активных задач: {len(jobs)}")
    for j in jobs:
        nrt = j.next_run_time
        nrt_str = "—"
        if nrt is not None:
            try:
                nrt_str = nrt.astimezone(TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
            except Exception:
                nrt_str = str(nrt)
        lines.append(f"• {j.id}: next={nrt_str}")

    lines.append(f"TZ: {TZ}")
    lines.append(f"ADMIN_CHAT_ID set: {_admin_status()}")

    def _probe(mod_name: str, fn_name: str) -> str:
        try:
            m = __import__(mod_name, fromlist=[fn_name])
            return "OK" if hasattr(m, fn_name) else "missing fn"
        except Exception as e:
            return f"error: {e.__class__.__name__}"

    for mod, fn in [
        ("crypto_monitor", "collect_new_coins"),
        ("reddit_monitor", "collect_signals"),
        ("ipo_monitor", "collect_ipos"),
    ]:
        lines.append(f"{mod}.{fn}: {_probe(mod, fn)}")

    lines.append("Подсказка: /summary_now — отправить сводку вручную.")
    return "\n".join(lines)
