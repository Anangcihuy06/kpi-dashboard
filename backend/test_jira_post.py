import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import requests, json, models
from database import SessionLocal
from encrypt import decrypt_val

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()
jira_url = setting.jira_url.rstrip('/')
auth = (setting.jira_email, decrypt_val(setting.jira_token_encrypted))

jql = 'assignee = "5de71ecb8743750d00b7fbf5" AND updated >= "2026-01-01" AND updated <= "2026-12-31"'
params = {
    "jql": jql,
    "maxResults": 100,
    "fields": ["summary", "description", "status", "project", "issuetype", "priority", "story_points", "resolutiondate", "created", "updated"]
}

r3 = requests.post(f"{jira_url}/rest/api/3/search", auth=auth, json=params)
data = r3.json()
print("POST /search", r3.status_code, "total=", data.get('total'), "issues len=", len(data.get('issues', [])))
