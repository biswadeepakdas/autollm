"""Simple APScheduler-based background scheduler for aggregation + suggestions.
In production, replace with Celery Beat or a separate cron service.
"""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.worker.aggregator import aggregate_daily_stats
from app.worker.suggestion_engine import generate_suggestions


scheduler = AsyncIOScheduler()


def start_scheduler():
    """Call from main app lifespan if you want in-process scheduling."""
    # Run daily stats aggregation at 2:00 AM UTC
    scheduler.add_job(
        aggregate_daily_stats,
        CronTrigger(hour=2, minute=0),
        id="daily_aggregation",
        replace_existing=True,
    )

    # Run suggestion engine at 3:00 AM UTC
    scheduler.add_job(
        generate_suggestions,
        CronTrigger(hour=3, minute=0),
        id="daily_suggestions",
        replace_existing=True,
    )

    scheduler.start()
    print("[Scheduler] Started — aggregation at 02:00 UTC, suggestions at 03:00 UTC")
