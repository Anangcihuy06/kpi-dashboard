import logging
import os
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from scheduler import (
    sync_sprints_job,
    sync_and_calculate_all_users_job,
    sync_attendance_nightly_job,
    SYNC_SPRINTS_INTERVAL_MINUTES,
    SYNC_KPI_CALCULATION_INTERVAL_MINUTES
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StandaloneWorker")

def run_worker():
    logger.info(f"Starting Standalone Worker...")
    logger.info(f"Intervals: Sprint sync every {SYNC_SPRINTS_INTERVAL_MINUTES} min, KPI calculation every {SYNC_KPI_CALCULATION_INTERVAL_MINUTES} min")
    
    scheduler = BlockingScheduler()
    
    scheduler.add_job(
        sync_sprints_job, 
        IntervalTrigger(minutes=SYNC_SPRINTS_INTERVAL_MINUTES), 
        id="sync_sprints_job", 
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=300
    )
    
    scheduler.add_job(
        sync_and_calculate_all_users_job, 
        IntervalTrigger(minutes=SYNC_KPI_CALCULATION_INTERVAL_MINUTES), 
        id="sync_calc_job", 
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=900
    )
    
    scheduler.add_job(
        sync_attendance_nightly_job,
        CronTrigger(hour=1, minute=0),
        id="sync_attendance_nightly",
        replace_existing=True,
        max_instances=1
    )
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker stopped.")

if __name__ == "__main__":
    run_worker()
