import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime

db = SessionLocal()

from_date = datetime(2026, 1, 1)
to_date = datetime(2026, 12, 31, 23, 59, 59)

users = db.query(models.User).filter(models.User.is_active == True).all()

completed_statuses = ["done", "resolved", "ready to release"]

print("=== COMPARE ALL ISSUES VS COMPLETED-ONLY ISSUES (2026) ===")
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
    
    for ji in jiras:
        r_date = ji.resolved_date or ji.updated_date or ji.created_date
        if r_date:
            try:
                r_dt = datetime.fromisoformat(str(r_date).replace('Z', '+00:00')) if isinstance(r_date, str) else r_date
                r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
                if from_date <= r_dt_naive <= to_date:
                    all_cnt += 1
                    if ji.status and ji.status.lower() in completed_statuses:
                        completed_cnt += 1
            except Exception:
                pass
                
    print(f"User: {u.full_name:<30} | All Counted: {all_cnt:<3} | Strictly Completed (Done/Resolved): {completed_cnt}")
