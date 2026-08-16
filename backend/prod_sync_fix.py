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
        
        # FIX: Ensure all users have Jira/GitLab placeholders so that the discovery engine doesn't skip them
        # Also patch known external IDs for proxy users created by HRIS login in prod
        KNOWN_MAPPINGS = {
            "01.04.19.1905": {"jira": "5de71ecb8743750d00b7fbf5", "gitlab": "anang"},
            "18.11.22.3063": {"jira": "63bbbbfa50b9490924dc02d0", "gitlab": "adian.rhamadhan"},
            "13.04.26.4918": {"jira": "5de480fe3384720d1879bce3", "gitlab": "billy93"},
            "06.01.23.3097": {"jira": "63bb8aeb2a526608c54f51a7", "gitlab": "ansha.cerbia"},
            "01.10.19.2239": {"jira": "5de8eafb7eb2280d03ca4f86", "gitlab": "bayu.prasetya"},
            "10.06.19.1979": {"jira": "5de71eba7eb2280d03ca30d6", "gitlab": "imamul.muttaqin"},
            "04.01.21.2435": {"jira": "6001479ad36496013924f9da", "gitlab": "azhari"},
            "05.03.18.1603": {"jira": "5de71ebe4ae7b80d0d1a28c4", "gitlab": "syailendra"}
        }

        for u in users:
            changed = False
            # Hardcoded patch for known users who failed auto-discovery in prod
            if u.nik in KNOWN_MAPPINGS:
                patch = KNOWN_MAPPINGS[u.nik]
                if not u.jira_account_id or u.jira_account_id.startswith("jira_user_"):
                    u.jira_account_id = patch["jira"]
                    changed = True
                if not u.gitlab_username or u.gitlab_username.startswith("gitlab_user_"):
                    u.gitlab_username = patch["gitlab"]
                    changed = True
                    
            if not u.jira_account_id:
                u.jira_account_id = f"jira_user_{u.id}"
                changed = True
            if not u.gitlab_username:
                u.gitlab_username = f"gitlab_user_{u.id}"
                changed = True
                
            if changed:
                db.commit()

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
