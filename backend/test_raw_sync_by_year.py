import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime
from feature_analyzer import calculate_feature_weight

db = SessionLocal()

def get_raw_user_metrics_for_year(user_id: str, year: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return {}
        
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31, 23, 59, 59)
    
    # 1. Jira Identities & Issues
    jira_ident = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == user_id,
        models.EmployeeIdentity.source == 'jira'
    ).first()
    
    jira_account_id = jira_ident.external_user_id if jira_ident else None
    
    jira_issues_count = 0
    jira_sp_sum = 0.0
    
    if jira_account_id:
        jira_issues = db.query(models.RawJiraIssue).filter(
            models.RawJiraIssue.assignee_account_id == jira_account_id
        ).all()
        
        for ji in jira_issues:
            # Check resolution or updated date for requested year
            r_date = ji.resolved_date or ji.updated_date or ji.created_date
            if r_date:
                r_dt = datetime.fromisoformat(str(r_date).replace('Z', '+00:00')) if isinstance(r_date, str) else r_date
                # Strip timezone for comparison
                r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
                
                if start_date <= r_dt_naive <= end_date:
                    jira_issues_count += 1
                    # Get story points or feature weight fallback
                    sp = ji.story_points or 0.0
                    if sp == 0.0 and ji.raw_data:
                        sp = calculate_feature_weight(ji.raw_data)
                    jira_sp_sum += float(sp)

    # 2. GitLab Identities & Commits
    gitlab_idents = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == user_id,
        models.EmployeeIdentity.source == 'gitlab'
    ).all()
    
    user_emails = [user.email] + [i.email for i in gitlab_idents if i.email]
    user_emails = [e.lower() for e in user_emails if e]
    
    gitlab_commits_count = 0
    if user_emails:
        commits = db.query(models.RawGitLabCommit).filter(
            models.RawGitLabCommit.committed_date >= start_date,
            models.RawGitLabCommit.committed_date <= end_date
        ).all()
        
        for c in commits:
            if c.author_email and c.author_email.lower() in user_emails:
                gitlab_commits_count += 1
                
    return {
        "user_id": user_id,
        "name": user.full_name,
        "year": year,
        "jira_issues_completed": jira_issues_count,
        "jira_story_points": jira_sp_sum,
        "gitlab_commits": gitlab_commits_count
    }

print("=== RAW JIRA & GITLAB METRICS PER YEAR ===")
for yr in [2024, 2025, 2026]:
    print(f"\n--- YEAR {yr} ---")
    for u in db.query(models.User).filter(models.User.is_active == True).all():
        res = get_raw_user_metrics_for_year(u.id, yr)
        print(f"User {u.id} ({u.full_name}): Jira Issues = {res['jira_issues_completed']}, Jira SP = {res['jira_story_points']}, Commits = {res['gitlab_commits']}")
