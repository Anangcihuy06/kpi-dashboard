import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from comprehensive_sync import sync_jira_issues, calculate_daily_aggregated_kpi
from datetime import datetime, timedelta

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()
users = db.query(models.User).all()

start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 12, 31)

print("=== RE-SYNCING ALL USERS WITH ARCHITECTURAL COMPLEXITY ENGINE ===")
for u in users:
    j_cnt = sync_jira_issues(db, u, setting, start_date, end_date)
    curr = start_date.date()
    end_d = end_date.date()
    while curr <= end_d:
        calculate_daily_aggregated_kpi(db, u, datetime.combine(curr, datetime.min.time()))
        curr += timedelta(days=1)
    print(f"User {u.id} ({u.full_name}): Synced {j_cnt} Jira issues.")

print("Resync finished successfully!")
