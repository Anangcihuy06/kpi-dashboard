import sys
import os
sys.path.append(os.getcwd())
from database import SessionLocal
import models
from comprehensive_sync import sync_jira_issues
from datetime import datetime

db = SessionLocal()
user = db.query(models.User).filter(models.User.nik == '01.04.19.1905').first()
settings = db.query(models.IntegrationSetting).first()

start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 12, 31)

count = sync_jira_issues(db, user, settings, start_date, end_date)
print(f"Synced {count} Jira issues for Nanang in 2026")
