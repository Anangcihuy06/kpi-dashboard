import sys, os
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

jql = 'assignee = "5de71ecb8743750d00b7fbf5"'
r = requests.get(f"{jira_url}/rest/api/3/search/jql", auth=auth, params={"jql": jql, "maxResults": 50}, timeout=15)

with open('c:/Users/ATI-User/KPI-Dashboard/backend/jira_out.json', 'w', encoding='utf-8') as f:
    f.write(r.text)
