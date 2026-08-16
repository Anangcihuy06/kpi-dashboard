import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from comprehensive_sync import sync_jira_issues
from datetime import datetime

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()
nanang = db.query(models.User).filter(models.User.id == '6518').first()

start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 12, 31)

print('Running sync_jira_issues for Nanang Wahyudi...')
count = sync_jira_issues(db, nanang, setting, start_date, end_date)
print(f'Synced {count} Jira issues!')

jira_activities = db.query(models.Activity).filter(
    models.Activity.user_id == '6518',
    models.Activity.source == 'jira'
).all()

print(f'Total Jira activities in DB for Nanang: {len(jira_activities)}')
total_sp = sum(a.story_points for a in jira_activities if a.story_points)
print(f'Total Story Points / Feature Weights for Nanang: {total_sp}')
