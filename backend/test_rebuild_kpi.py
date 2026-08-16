import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from comprehensive_sync import sync_jira_issues, calculate_daily_aggregated_kpi
from feature_analyzer import calculate_feature_weight
from datetime import datetime, timedelta

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()
nanang = db.query(models.User).filter(models.User.id == '6518').first()

with open('c:/Users/ATI-User/KPI-Dashboard/backend/rebuild_test.txt', 'w', encoding='utf-8') as f:
    raw_f20m = db.query(models.RawJiraIssue).filter(models.RawJiraIssue.issue_key == 'F20M-27').first()
    if raw_f20m and raw_f20m.raw_data:
        weight_f20m = calculate_feature_weight(raw_f20m.raw_data)
        f.write(f"=== F20M-27 DYNAMIC ARCHITECTURAL COMPLEXITY WEIGHT: {weight_f20m} SP ===\n")
    
    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 12, 31)

    sync_jira_issues(db, nanang, setting, start_date, end_date)

    curr = start_date.date()
    end_d = end_date.date()
    while curr <= end_d:
        calculate_daily_aggregated_kpi(db, nanang, datetime.combine(curr, datetime.min.time()))
        curr += timedelta(days=1)

    tot_sp = db.query(models.Activity).filter(
        models.Activity.user_id == '6518',
        models.Activity.source == 'jira'
    ).all()

    sum_sp = sum(a.story_points for a in tot_sp if a.story_points)
    f.write(f"UPDATED TOTAL STORY POINTS / FEATURE WEIGHTS FOR NANANG: {sum_sp} SP\n")
