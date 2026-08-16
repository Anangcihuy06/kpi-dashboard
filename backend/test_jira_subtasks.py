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
    "fields": "summary,issuetype,parent,subtasks",
    "maxResults": 100,
    "startAt": 0
}
response = requests.get(search_url, auth=jira_auth, params=params)
data = response.json()
issues = data.get("issues", [])

subtask_count = 0
for issue in issues:
    fields = issue.get("fields", {})
    issuetype = fields.get("issuetype", {}).get("name", "")
    if issuetype == "Sub-task":
        subtask_count += 1

print(f"Total returned: {len(issues)}")
print(f"Sub-tasks: {subtask_count}")

