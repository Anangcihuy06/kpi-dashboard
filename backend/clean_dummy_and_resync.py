import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from comprehensive_sync import sync_jira_issues, calculate_daily_aggregated_kpi
from datetime import datetime, timedelta

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()

# 1. Deactivate dummy user 7817 (Andreas a Billy Sutandi - dummy email)
dummy_billy = db.query(models.User).filter(models.User.id == '7817').first()
if dummy_billy:
    dummy_billy.is_active = False
    db.commit()
    print("Deactivated dummy user 7817 (andreas.dummy@atibusinessgroup.com)")

# 2. Resync all active users
users = db.query(models.User).filter(models.User.is_active == True).all()
start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 12, 31)

print(f"\nResyncing {len(users)} active users...")
for u in users:
    sync_jira_issues(db, u, setting, start_date, end_date)
    curr = start_date.date()
    end_d = end_date.date()
    while curr <= end_d:
        calculate_daily_aggregated_kpi(db, u, datetime.combine(curr, datetime.min.time()))
        curr += timedelta(days=1)
    print(f"Done user {u.id} ({u.full_name})")

print("\nResync finished successfully!")
