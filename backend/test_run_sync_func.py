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

from comprehensive_sync import sync_jira_issues, sync_jira_worklogs, sync_gitlab_commits, sync_gitlab_merge_requests

issues_synced = sync_jira_issues(db, user, settings, start_date, end_date)
print(f"Issues synced by function: {issues_synced}")

wl_synced = sync_jira_worklogs(db, user, settings, start_date, end_date)
print(f"Worklogs synced by function: {wl_synced}")

# Commits and MRs
commits = sync_gitlab_commits(db, user, settings, start_date, end_date)
print(f"Commits synced: {commits}")

mrs = sync_gitlab_merge_requests(db, user, settings, start_date, end_date)
print(f"MRs synced: {mrs}")
