from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler() -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.recurring_service import process_due_rules

    async def _job() -> None:
        async with AsyncSessionLocal() as db:
            await process_due_rules(db)

    scheduler.add_job(_job, CronTrigger(hour=0, minute=5), id="process_recurring", replace_existing=True)
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
