import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime
from feature_analyzer import calculate_feature_weight
from founder_engine import get_founder_credits_for_user

db = SessionLocal()

def calculate_dynamic_global_max_sp(year: int):
    from_date = datetime(year, 1, 1)
    to_date = datetime(year, 12, 31, 23, 59, 59)
    
    users = db.query(models.User).filter(models.User.is_active == True).all()
    user_sp_map = {}
    
    for u in users:
        tot_sp = 0.0
        
        # 1. Jira Raw SP & Feature Weights
        jira_ident = db.query(models.EmployeeIdentity).filter(
            models.EmployeeIdentity.user_id == u.id,
            models.EmployeeIdentity.source == 'jira'
        ).first()
        
        if jira_ident and jira_ident.external_user_id:
            jiras = db.query(models.RawJiraIssue).filter(
                models.RawJiraIssue.assignee_account_id == jira_ident.external_user_id
            ).all()
            
            for ji in jiras:
                r_date = ji.resolved_date or ji.updated_date or ji.created_date
                if r_date:
                    try:
                        r_dt = datetime.fromisoformat(str(r_date).replace('Z', '+00:00')) if isinstance(r_date, str) else r_date
                        r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
                        if from_date <= r_dt_naive <= to_date:
                            sp = ji.story_points or 0.0
                            if sp == 0.0 and ji.raw_data:
                                sp = calculate_feature_weight(ji.raw_data)
                            tot_sp += float(sp)
                    except Exception:
                        pass
                        
        # 2. Founder Credit for target year
        founder_sp = get_founder_credits_for_user(u.id, target_year=year)
        tot_sp += founder_sp
        
        user_sp_map[u.full_name] = tot_sp
        
    team_max_sp = max(user_sp_map.values(), default=1.0)
    return team_max_sp, user_sp_map

for yr in [2025, 2026]:
    max_sp, sp_map = calculate_dynamic_global_max_sp(yr)
    print(f"=== DYNAMIC TEAM MAX SP FOR YEAR {yr}: {max_sp} SP ===")
    for uname, sp in sp_map.items():
        print(f" - {uname}: {sp} SP (Score vs max: {round((sp/max_sp)*100, 2)}%)")
