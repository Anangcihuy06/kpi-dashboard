import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from comprehensive_sync import sync_jira_issues, sync_gitlab_commits, calculate_daily_aggregated_kpi
from datetime import datetime, timedelta

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()
users = db.query(models.User).filter(models.User.is_active == True).all()

start_2025 = datetime(2025, 1, 1)
end_2025 = datetime(2025, 12, 31)

print(f"=== POPULATING 2025 DAILY KPIS FOR {len(users)} ACTIVE USERS ===")

for u in users:
    print(f"Populating 2025 for {u.full_name} (ID {u.id})...")
    curr = start_2025.date()
    end_d = end_2025.date()
    while curr <= end_d:
        calculate_daily_aggregated_kpi(db, u, datetime.combine(curr, datetime.min.time()))
        curr += timedelta(days=1)
    print(f"   Done 2025 daily KPI records for {u.full_name}!")

print("\n2025 DAILY KPI POPULATION FINISHED!")
