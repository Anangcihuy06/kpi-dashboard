import os
import sys
import logging
from datetime import datetime, timedelta
sys.path.append(os.getcwd())

from database import SessionLocal
import models
from comprehensive_sync import sync_user_comprehensive, calculate_daily_aggregated_kpi
from comprehensive_sync import sync_user_comprehensive, calculate_daily_aggregated_kpi

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FullResyncClean")

def clean_database(db):
    """Wipe out all previously collected dummy or incomplete data"""
    logger.info("WIPING OLD DATA to ensure 100% real data...")
    try:
        # Delete raw jira issues because they were missing description/subtasks
        deleted_jira = db.query(models.RawJiraIssue).delete()
        logger.info(f"Deleted {deleted_jira} old RawJiraIssue records.")
        
        # Delete activities (removes dummy Gitlab & Jira)
        deleted_act = db.query(models.Activity).delete()
        logger.info(f"Deleted {deleted_act} old Activity records.")
        
        # Delete daily kpi (removes aggregated dummy data)
        deleted_kpi = db.query(models.KPIEmployeeDaily).delete()
        logger.info(f"Deleted {deleted_kpi} old KPIEmployeeDaily records.")
        
        # Delete attendance records (removes dummy attendance)
        deleted_att = db.query(models.AttendanceRecord).delete()
        logger.info(f"Deleted {deleted_att} old Attendance records.")
        
        db.commit()
        logger.info("Database wipe completed successfully.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error during database wipe: {e}")
        raise

def run_full_resync():
    db = SessionLocal()
    try:
        clean_database(db)
        
        logger.info("Syncing Attendance globally for all users via save_attendance_fixed.py...")
        os.system("python save_attendance_fixed.py")
        
        settings = db.query(models.IntegrationSetting).first()
        if not settings:
            logger.error("No integration settings found. Aborting.")
            return

        active_users = db.query(models.User).filter(models.User.is_active == True).all()
        logger.info(f"Found {len(active_users)} active users to resync.")
        
        target_year = 2026
        start_date = datetime(target_year, 1, 1)
        # Using today for end date
        end_date = datetime.now()
        
        for user in active_users:
            logger.info(f"--- RESYNCING USER: {user.full_name} ({user.nik}) ---")
            
            # 1. Sync HRIS Attendance (Handled globally before the loop now)
            # 2. Sync Jira & GitLab
            try:
                sync_user_comprehensive(db, user, settings, start_date, end_date)
                logger.info(f"Jira/Gitlab synced successfully.")
            except Exception as e:
                logger.error(f"Failed to sync Jira/Gitlab for {user.full_name}: {e}")
                
            # 3. Recalculate Daily KPI
            try:
                curr = start_date.date()
                end_d = end_date.date()
                while curr <= end_d:
                    calculate_daily_aggregated_kpi(db, user, datetime.combine(curr, datetime.min.time()))
                    curr += timedelta(days=1)
                db.commit()
                logger.info(f"Daily KPIs recalculated successfully.")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to recalculate KPIs for {user.full_name}: {e}")
                
        logger.info("====================================")
        logger.info("FULL RESYNC AND RECALCULATION DONE.")
        logger.info("====================================")
    finally:
        db.close()

if __name__ == "__main__":
    run_full_resync()
