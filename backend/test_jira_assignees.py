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
settings = db.query(models.IntegrationSetting).first()

jira_token = decrypt_val(settings.jira_token_encrypted)
jira_auth = (settings.jira_email, jira_token)
jira_url = settings.jira_url.rstrip("/")
account_id = jira_id.external_user_id

search_url = f"{jira_url}/rest/api/3/search/jql"
jql = f'assignee = "{account_id}" AND updated >= "2026-01-01" AND updated <= "2026-12-31"'

params = {
    "jql": jql,
    "fields": "summary",
    "maxResults": 100,
    "startAt": 0
}
response = requests.get(search_url, auth=jira_auth, params=params)
issues = response.json().get("issues", [])

issue_keys = [i["key"] for i in issues]

db_issues = db.query(models.RawJiraIssue).filter(
    models.RawJiraIssue.issue_key.in_(issue_keys)
).all()

assignees = {}
for i in db_issues:
    assignees[i.assignee_account_id] = assignees.get(i.assignee_account_id, 0) + 1

print(f"Total found in DB: {len(db_issues)}")
print("Assignees:")
for acc_id, cnt in assignees.items():
    emp = db.query(models.EmployeeIdentity).filter(models.EmployeeIdentity.external_user_id == acc_id).first()
    name = emp.user.full_name if emp and emp.user else "Unknown"
    print(f" - {name} ({acc_id}): {cnt}")

