import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime
from feature_analyzer import calculate_feature_weight
from founder_engine import get_founder_credits_for_user

db = SessionLocal()

from_date = datetime(2026, 1, 1)
to_date = datetime(2026, 12, 31, 23, 59, 59)
users = db.query(models.User).filter(models.User.is_active == True).all()

allowed_statuses = ["done", "resolved", "ready to release", "ready for uat", "uat (user)", "ready for qa", "in qa"]

print("=== LEADERBOARD WITH STRICT STATUS FILTERING ===")
for u in users:
    j_ident = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == u.id,
        models.EmployeeIdentity.source == 'jira'
    ).first()
    
    if not j_ident or not j_ident.external_user_id:
        continue
        
    jiras = db.query(models.RawJiraIssue).filter(
        models.RawJiraIssue.assignee_account_id == j_ident.external_user_id
    ).all()
    
    all_cnt = 0
    completed_cnt = 0
    completed_keys = []
    incomplete_keys = []
    
    for ji in jiras:
        r_date = ji.resolved_date or ji.updated_date or ji.created_date
        if r_date:
            try:
                r_dt = datetime.fromisoformat(str(r_date).replace('Z', '+00:00')) if isinstance(r_date, str) else r_date
                r_dt_naive = r_dt.replace(tzinfo=None)
                if from_date <= r_dt_naive <= to_date:
                    all_cnt += 1
                    status_lower = (ji.status or "").lower()
                    if status_lower in allowed_statuses:
                        completed_cnt += 1
                        completed_keys.append((ji.issue_key, ji.status))
                    else:
                        incomplete_keys.append((ji.issue_key, ji.status))
            except Exception:
                pass
                
    print(f"User: {u.full_name:<30}")
    print(f"   - Total Counted in 2026 (Unfiltered): {all_cnt}")
    print(f"   - Strictly Completed in 2026: {completed_cnt}")
    print(f"   - Completed Tasks: {completed_keys[:5]}")
    print(f"   - Incomplete Tasks (To Do / Backlog / Dev / Review): {incomplete_keys[:5]}")
