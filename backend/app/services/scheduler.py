"""
Background Scheduler for Analytics
==================================

Handles scheduled tasks like fetching Instagram insights periodically.
"""

import asyncio
import logging
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.app.db.base import SessionLocal
from backend.app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

# Create scheduler instance
scheduler = AsyncIOScheduler()


async def fetch_all_insights_job():
    """
    Background job to fetch insights for all campaigns.
    
    This runs periodically to keep analytics data up-to-date
    by fetching the latest metrics from Instagram API.
    """
    logger.info("🔄 Running scheduled insights fetch...")
    
    db = SessionLocal()
    try:
        service = AnalyticsService(db)
        results = await service.fetch_all_campaign_insights()
        
        success_count = sum(1 for r in results if r.get("success"))
        total = len(results)
        
        logger.info(f"✅ Fetched insights for {success_count}/{total} campaigns")
        
        # Log failed fetches for debugging
        failed = [r for r in results if not r.get("success")]
        if failed:
            for failure in failed:
                logger.warning(f"Failed to fetch insights: {failure.get('error')}")
                
    except Exception as e:
        logger.error(f"❌ Scheduled insights fetch failed: {e}", exc_info=True)
    finally:
        db.close()


def start_scheduler():
    """
    Start the background scheduler.
    
    Schedules:
    - Insights fetching: Every hour
    """
    if scheduler.running:
        logger.warning("Scheduler is already running")
        return
    
    # Add job to fetch insights every hour
    scheduler.add_job(
        fetch_all_insights_job,
        'interval',
        hours=1,
        id='fetch_insights',
        replace_existing=True,
        max_instances=1  # Prevent overlapping executions
    )
    
    scheduler.start()
    logger.info("📅 Scheduler started - Insights will be fetched every hour")


def stop_scheduler():
    """Stop the background scheduler."""
    if not scheduler.running:
        logger.warning("Scheduler is not running")
        return
    
    scheduler.shutdown(wait=False)
    logger.info("📅 Scheduler stopped")


def pause_scheduler():
    """Pause the scheduler without shutting it down."""
    if not scheduler.running:
        logger.warning("Scheduler is not running")
        return
    
    scheduler.pause()
    logger.info("⏸️ Scheduler paused")


def resume_scheduler():
    """Resume a paused scheduler."""
    if not scheduler.running:
        logger.warning("Scheduler is not running")
        return
    
    scheduler.resume()
    logger.info("▶️ Scheduler resumed")


def get_scheduler_status() -> dict:
    """Get current scheduler status."""
    jobs = scheduler.get_jobs()
    
    return {
        "running": scheduler.running,
        "jobs": [
            {
                "id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in jobs
        ]
    }


# Optional: Add more scheduled jobs here
async def cleanup_old_data_job():
    """
    Clean up old analytics data (optional).
    
    Remove click events and insights older than X days
    to keep database size manageable.
    """
    logger.info("🧹 Running data cleanup job...")
    # TODO: Implement cleanup logic
    pass


def schedule_cleanup_job(days_to_keep: int = 90):
    """
    Schedule a job to clean up old data.
    
    Args:
        days_to_keep: Number of days of data to retain
    """
    scheduler.add_job(
        cleanup_old_data_job,
        'cron',
        hour=2,  # Run at 2 AM
        day='*/7',  # Every 7 days
        id='cleanup_old_data',
        replace_existing=True
    )
    logger.info(f"🧹 Scheduled cleanup job (keeping {days_to_keep} days of data)")
