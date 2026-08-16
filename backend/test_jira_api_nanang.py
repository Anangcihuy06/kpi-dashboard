import sys
import os
sys.path.append(os.getcwd())
from database import SessionLocal
import models
import requests
from datetime import datetime

db = SessionLocal()
user = db.query(models.User).filter(models.User.nik == '01.04.19.1905').first()
jira_identity = db.query(models.EmployeeIdentity).filter(
    models.EmployeeIdentity.user_id == user.id,
    models.EmployeeIdentity.source == "jira"
).first()
settings = db.query(models.IntegrationSetting).first()

jira_auth = (settings.jira_email, settings.jira_token)
jira_url = settings.jira_url.rstrip("/")
account_id = jira_identity.external_user_id

search_url = f"{jira_url}/rest/api/3/search/jql"
jql = f'assignee = "{account_id}" AND updated >= "2026-01-01" AND updated <= "2026-12-31"'

start_at = 0
max_results = 100

total_issues = 0
while True:
    params = {
        "jql": jql,
        "fields": "summary,status",
        "maxResults": max_results,
        "startAt": start_at
    }
    
    response = requests.get(search_url, auth=jira_auth, params=params, timeout=30)
    data = response.json()
    issues = data.get("issues", [])
    total = data.get("total", 0)
    print(f"StartAt {start_at}, Total {total}, Issues {len(issues)}")
    total_issues += len(issues)
    
    start_at += max_results
    if start_at >= total:
        break

print("Grand total:", total_issues)
