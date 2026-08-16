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

print(f"=== SYNCING YEAR 2025 METRICS FOR {len(users)} ACTIVE USERS ===")

for u in users:
    print(f"Syncing year 2025 for {u.full_name} (ID {u.id})...")
    # 1. Sync GitLab Commits for 2025
    g_cnt = sync_gitlab_commits(db, u, setting, start_2025, end_2025)
    
    # 2. Sync Jira Issues for 2025
    j_cnt = sync_jira_issues(db, u, setting, start_2025, end_2025)
    
    # 3. Calculate daily aggregated KPIs for 2025
    curr = start_2025.date()
    end_d = end_2025.date()
    while curr <= end_d:
        calculate_daily_aggregated_kpi(db, u, datetime.combine(curr, datetime.min.time()))
        curr += timedelta(days=1)
        
    print(f"   Done {u.full_name}: {g_cnt} GitLab commits, {j_cnt} Jira issues synced for 2025!")

print("\nYEAR 2025 SYNC COMPLETED SUCCESSFULLY!")
