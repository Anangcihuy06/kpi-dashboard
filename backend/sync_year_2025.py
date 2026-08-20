import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from comprehensive_sync import sync_jira_issues, sync_gitlab_commits, calculate_daily_aggregated_kpi
from yearly_kpi_engine import get_rule_and_metrics_for_user
from datetime import datetime, timedelta
import collections

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
    
    # 3. Calculate daily aggregated KPIs for 2025 (Optimized with Preloading)
    print("   Preloading data for KPI calculation to avoid N+1 queries...")
    activities = db.query(models.Activity).filter(
        models.Activity.user_id == u.id,
        models.Activity.activity_date >= start_2025.date(),
        models.Activity.activity_date <= end_2025.date()
    ).all()
    
    activities_by_date = collections.defaultdict(list)
    for act in activities:
        activities_by_date[act.activity_date].append(act)
        
    rule, metrics_defs = get_rule_and_metrics_for_user(db, u)
    
    preloaded_context = {
        "activities_by_date": activities_by_date,
        "rule_metrics": (rule, metrics_defs),
        "attendance_by_date": {} # fallback is handled in function
    }
    
    curr = start_2025.date()
    end_d = end_2025.date()
    days_processed = 0
    while curr <= end_d:
        calculate_daily_aggregated_kpi(db, u, datetime.combine(curr, datetime.min.time()), preloaded=preloaded_context)
        curr += timedelta(days=1)
        days_processed += 1
        
    print(f"   Done {u.full_name}: {g_cnt} GitLab commits, {j_cnt} Jira issues, {days_processed} KPI days synced!")

print("\nYEAR 2025 SYNC COMPLETED SUCCESSFULLY!")
