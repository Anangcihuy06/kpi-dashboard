import sys
from datetime import datetime
import logging
logging.basicConfig(level=logging.INFO)

sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from comprehensive_sync import sync_jira_issues

db = SessionLocal()
settings = db.query(models.IntegrationSetting).first()
start_date = datetime(2026, 1, 1, 0, 0, 0)
end_date = datetime(2026, 12, 31, 23, 59, 59)

for user in db.query(models.User).all():
    print(f"Testing {user.full_name}...")
    try:
        sync_jira_issues(db, user, settings, start_date, end_date)
    except Exception as e:
        print(f"Error for {user.full_name}: {e}")
