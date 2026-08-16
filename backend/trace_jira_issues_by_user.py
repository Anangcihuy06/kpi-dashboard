import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime
from feature_analyzer import calculate_feature_weight

db = SessionLocal()

target_users = ['9615', '6592', '7052', '6518', '7690']  # Billy, Imamul, Fadli, Nanang, Adian
from_date = datetime(2026, 1, 1)
to_date = datetime(2026, 12, 31, 23, 59, 59)

print("=== TRACING EXACT JIRA ISSUES & PROJECTS FOR FEATURE ARCHITECTURAL WEIGHT (2026) ===")

for uid in target_users:
    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user:
        continue
        
    jira_ident = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == uid,
        models.EmployeeIdentity.source == 'jira'
    ).first()
    
    print(f"\n==========================================================================================")
    print(f"USER: {user.full_name} (ID: {uid} | Jira Account: {jira_ident.external_user_id if jira_ident else 'NONE'})")
    print(f"==========================================================================================")
    
    if not jira_ident or not jira_ident.external_user_id:
        print("   NO JIRA ACCOUNT LINKED!")
        continue
        
    jiras = db.query(models.RawJiraIssue).filter(
        models.RawJiraIssue.assignee_account_id == jira_ident.external_user_id
    ).all()
    
    user_issues = []
    tot_weight = 0.0
    
    for ji in jiras:
        r_date = ji.resolved_date or ji.updated_date or ji.created_date
        if r_date:
            try:
                r_dt = datetime.fromisoformat(str(r_date).replace('Z', '+00:00')) if isinstance(r_date, str) else r_date
                r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
                if from_date <= r_dt_naive <= to_date:
                    sp = float(ji.story_points or 0.0)
                    cw = calculate_feature_weight(ji.raw_data or {})
                    tot_w = sp + cw
                    tot_weight += tot_w
                    
                    fields = ji.raw_data.get('fields', {}) if ji.raw_data else {}
                    proj = fields.get('project', {}).get('name') or fields.get('project', {}).get('key', 'UNKNOWN')
                    summary = fields.get('summary', ji.issue_key)
                    subtasks = fields.get('subtasks', [])
                    
                    user_issues.append({
                        "key": ji.issue_key,
                        "project": proj,
                        "summary": summary,
                        "sp": sp,
                        "feature_weight": cw,
                        "total_weight": tot_w,
                        "subtasks_count": len(subtasks)
                    })
            except Exception as e:
                pass
                
    print(f"Total Completed Jira Issues: {len(user_issues)} | Total Feature Complexity Weight: {tot_weight} pts\n")
    print(f"{'Issue Key':<12} | {'Project Name / Key':<25} | {'SP':<5} | {'FeatWeight':<10} | {'Summary':<45}")
    print("-" * 105)
    for iss in user_issues[:15]:  # Show top 15 issues
        print(f"{iss['key']:<12} | {iss['project']:<25} | {iss['sp']:<5.1f} | {iss['feature_weight']:<10.1f} | {iss['summary'][:44]:<45}")
    if len(user_issues) > 15:
        print(f"... and {len(user_issues) - 15} more issues.")
