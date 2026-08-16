import sys
import os
sys.path.append(os.getcwd())
from database import SessionLocal
import models
from datetime import datetime

db = SessionLocal()
jira_id = db.query(models.EmployeeIdentity).filter(
    models.EmployeeIdentity.user_id == '6518',
    models.EmployeeIdentity.source == 'jira'
).first()

issues = db.query(models.RawJiraIssue).filter(
    models.RawJiraIssue.assignee_account_id == jira_id.external_user_id
).all()

count_valid = 0
for ji in issues:
    status = (ji.status or "").lower()
    if status in ["done", "resolved", "ready to release", "ready for uat", "uat (user)", "ready for qa", "in qa"]:
        count_valid += 1
print(f"Total issues: {len(issues)}, Valid status: {count_valid}")
