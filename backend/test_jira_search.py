import sys
import os
import datetime
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import requests, json, models
from database import SessionLocal
from encrypt import decrypt_val

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()

jira_url = setting.jira_url.rstrip('/')
jira_email = setting.jira_email
jira_token = decrypt_val(setting.jira_token_encrypted)
auth = (jira_email, jira_token)

account_id = "5de71ecb8743750d00b7fbf5"
start_date = datetime.datetime(2026, 1, 1)
end_date = datetime.datetime(2026, 12, 31)

jql = f'assignee = "{account_id}" AND updated >= "{start_date.date()}" AND updated <= "{end_date.date()}"'

payload = {
    "jql": jql,
    "fields": ["summary", "description", "subtasks", "status", "project", "issuetype", "priority", "story_points", "customfield_10024", "customfield_10016", "customfield_10028", "resolutiondate", "created", "updated"],
    "maxResults": 100,
    "startAt": 0
}

r = requests.post(f"{jira_url}/rest/api/3/search/jql", auth=auth, json=payload, timeout=15)
print(r.status_code)
if r.status_code == 200:
    print(json.dumps(r.json(), indent=2)[:500])
else:
    print(r.text)
