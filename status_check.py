import os
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Riga")

async def build_status(context) -> str:
    sched = context.application.bot_data.get('scheduler')
    jobs = sched.get_jobs() if sched else []
    lines = [
        "Статус: OK",
        f"TZ: {TZ}",
        f"Активных задач: {len(jobs)}",
        f"ADMIN_CHAT_ID set: {'yes' if os.getenv('ADMIN_CHAT_ID') else 'no'}",
    ]
    for j in jobs:
        lines.append(f"• {j.id}: next={j.next_run_time}")
    return "\n".join(lines)
