import sys
import os
sys.path.append(os.getcwd())
from database import SessionLocal
import models
import requests
from encrypt import decrypt_val

db = SessionLocal()
user = db.query(models.User).filter(models.User.nik == '01.04.19.1905').first()
jira_id = db.query(models.EmployeeIdentity).filter(
    models.EmployeeIdentity.user_id == user.id,
    models.EmployeeIdentity.source == 'jira'
).first()

issues = db.query(models.RawJiraIssue).filter(
    models.RawJiraIssue.assignee_account_id == jira_id.external_user_id
).all()

statuses = {}
for ji in issues:
    status = (ji.status or "").lower()
    statuses[status] = statuses.get(status, 0) + 1

print(f"Total in DB: {len(issues)}")
print("Statuses:")
for s, c in statuses.items():
    print(f" - {s}: {c}")

