import sys
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

jql = 'assignee = "5de71ecb8743750d00b7fbf5" AND updated >= "2026-01-01" AND updated <= "2026-12-31"'
params = {
    "jql": jql,
    "maxResults": 100,
    "fields": "summary,updated",
}
r = requests.get(f"{jira_url}/rest/api/3/search/jql", auth=auth, params=params, timeout=15)
if r.status_code == 200:
    issues = r.json().get('issues', [])
    print(f"Issues in 2026: {len(issues)}")
    if issues:
        print(f"First issue in 2026: {issues[0]['key']} updated {issues[0]['fields']['updated']}")
else:
    print(r.status_code, r.text)

jql_no_date = 'assignee = "5de71ecb8743750d00b7fbf5"'
params_no_date = {
    "jql": jql_no_date,
    "maxResults": 100,
    "fields": "summary,updated",
}
r2 = requests.get(f"{jira_url}/rest/api/3/search/jql", auth=auth, params=params_no_date, timeout=15)
if r2.status_code == 200:
    issues = r2.json().get('issues', [])
    print(f"Issues no date: {len(issues)}")
