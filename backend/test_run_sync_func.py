import sys
from datetime import datetime
import logging
logging.basicConfig(level=logging.INFO)

sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from comprehensive_sync import sync_jira_issues

db = SessionLocal()

user = db.query(models.User).filter(models.User.full_name.ilike('%Nanang%')).first()
settings = db.query(models.IntegrationSetting).first()

start_date = datetime(2026, 1, 1, 0, 0, 0)
end_date = datetime(2026, 12, 31, 23, 59, 59)

issues_synced = sync_jira_issues(db, user, settings, start_date, end_date)
print(f"Issues synced by function: {issues_synced}")
