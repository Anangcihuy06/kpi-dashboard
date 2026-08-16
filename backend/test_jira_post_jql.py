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
payload = {
    "jql": jql,
    "maxResults": 100,
    "fields": ["summary", "description", "status", "project", "issuetype", "priority", "story_points", "resolutiondate", "created", "updated"]
}

r4 = requests.post(f"{jira_url}/rest/api/3/search/jql", auth=auth, json=payload)
print("POST /search/jql", r4.status_code, "total=", r4.json().get('total'), "issues len=", len(r4.json().get('issues', [])))
