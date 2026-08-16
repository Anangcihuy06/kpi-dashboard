import sys
import os
sys.path.append(os.getcwd())
import logging
from database import SessionLocal
import models
from datetime import datetime
from comprehensive_sync import sync_jira_issues

logging.basicConfig(level=logging.ERROR)

db = SessionLocal()

# Delete Nanang's issues from DB first!
jira_id = '712020:6b5b5b03-9b43-4c9c-b5f7-6b3a3c20058b'
db.query(models.Activity).filter(models.Activity.source == 'jira').delete()
db.query(models.RawJiraIssue).filter(models.RawJiraIssue.assignee_account_id == jira_id).delete()
db.commit()

user = db.query(models.User).filter(models.User.nik == '01.04.19.1905').first()
settings = db.query(models.IntegrationSetting).first()

start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 12, 31)

issues_synced = sync_jira_issues(db, user, settings, start_date, end_date)
print(f"Synced {issues_synced} for Nanang")
