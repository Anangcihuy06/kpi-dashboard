from database import SessionLocal
import models
from datetime import datetime

db = SessionLocal()

# Jira check
jira_id = db.query(models.EmployeeIdentity).filter(
    models.EmployeeIdentity.user_id == '6518',
    models.EmployeeIdentity.source == 'jira'
).first()

print(f"Jira external_user_id: {jira_id.external_user_id}")

issues = db.query(models.RawJiraIssue).filter(
    models.RawJiraIssue.assignee_account_id == jira_id.external_user_id
).all()

print(f"Total raw issues: {len(issues)}")

f = datetime(2026, 1, 1)
t = datetime(2026, 12, 31)

cnt = 0
sp = 0.0
for ji in issues:
    r_dt_naive = None
    if ji.resolved_date:
        r_dt = ji.resolved_date
        r_dt_naive = r_dt.replace(tzinfo=None) if hasattr(r_dt, 'replace') else r_dt
    
    if r_dt_naive and f <= r_dt_naive <= t:
        status_lower = (ji.status or '').lower()
        if status_lower in ['done', 'resolved', 'ready to release', 'ready for uat', 'uat (user)', 'ready for qa', 'in qa']:
            cnt += 1
            sp += float(ji.story_points or 0.0)
        else:
            print(f"  Skipped (status={status_lower}): {ji.issue_key}")

print(f"Jira completed in date range: {cnt}, SP: {sp}")

# Also check activities 
activities = db.query(models.Activity).filter(
    models.Activity.user_id == '6518',
    models.Activity.activity_date >= f,
    models.Activity.activity_date <= t
).all()

print(f"Activities in range: {len(activities)}")
from collections import Counter
src_types = Counter()
for a in activities:
    src_types[f"{a.source}:{a.activity_type}"] += 1
print(f"By source:type: {dict(src_types)}")

db.close()
