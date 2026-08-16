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
    "maxResults": 5,
    "fields": "summary,description,status,project,issuetype"
}

r1 = requests.get(f"{jira_url}/rest/api/3/search", auth=auth, params=params)
print("GET /search", r1.status_code, r1.text[:200])

r2 = requests.get(f"{jira_url}/rest/api/3/search/jql", auth=auth, params=params)
print("GET /search/jql", r2.status_code, r2.text[:200])

r3 = requests.post(f"{jira_url}/rest/api/3/search", auth=auth, json=params)
print("POST /search", r3.status_code, r3.text[:200])
