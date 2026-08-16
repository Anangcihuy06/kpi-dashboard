import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models
from sync_service import sync_attendance_for_year, sync_yearly_user_metrics
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def run_prod_sync():
    db = SessionLocal()
    try:
        # Get all active users in the database
        users = db.query(models.User).filter(
            models.User.is_active == True
        ).all()
        
        logger.info(f"Found {len(users)} active users to sync.")
        
        # 1. Sync Attendance for 2026 for all these users
        logger.info("--- 1. SYNCING ATTENDANCE FOR 2026 ---")
        try:
            sync_attendance_for_year(db, users, 2026)
            logger.info("Attendance sync completed successfully.")
        except Exception as e:
            logger.error(f"Failed to sync attendance: {e}")
            
        # 2. Get Integration Settings
        settings = db.query(models.IntegrationSetting).first()
        if not settings:
            logger.error("Integration settings missing! Cannot sync Jira/Gitlab.")
            return

        # 3. Comprehensive Sync for Jira and Gitlab and rebuild KPIEmployeeDaily
        logger.info("--- 2. SYNCING JIRA/GITLAB & REBUILDING DAILY KPIs ---")
        for u in users:
            logger.info(f"Syncing comprehensive data for user: {u.full_name}...")
            
            # Delete corrupted daily cache for Jan 1 2026 specifically if it exists
            # to ensure the backend recalculates it correctly
            corrupted = db.query(models.KPIEmployeeDaily).filter(
                models.KPIEmployeeDaily.user_id == u.id,
                models.KPIEmployeeDaily.date == datetime(2026, 1, 1).date(),
                models.KPIEmployeeDaily.attendance_days == 0
            ).first()
            if corrupted:
                db.delete(corrupted)
                db.commit()
                
            try:
                # This will sync Gitlab, Jira, and aggregate attendance into KPIEmployeeDaily
                sync_yearly_user_metrics(db, u, 2026, settings)
                logger.info(f"Success for {u.full_name}.")
            except Exception as e:
                logger.error(f"Failed for {u.full_name}: {e}")
                
        logger.info("--- PROD FIX COMPLETED ---")
        logger.info("Silakan cek kembali dashboard frontend, data seharusnya sudah terisi penuh.")
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_prod_sync()
