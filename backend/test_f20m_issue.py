import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import requests
import json
import models
from database import SessionLocal
from encrypt import decrypt_val

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()

jira_url = setting.jira_url.rstrip('/')
jira_email = setting.jira_email
jira_token = decrypt_val(setting.jira_token_encrypted)
auth = (jira_email, jira_token)

print(f"Connecting to Jira: {jira_url}")

# 1. Get issue F20M-27
url_issue = f"{jira_url}/rest/api/3/issue/F20M-27"
r_issue = requests.get(url_issue, auth=auth, timeout=10)

with open('c:/Users/ATI-User/KPI-Dashboard/backend/f20m_27.json', 'w', encoding='utf-8') as f:
    if r_issue.status_code == 200:
        f.write(json.dumps(r_issue.json(), indent=2))
        print("F20M-27 fetched successfully!")
    else:
        f.write(f"Error {r_issue.status_code}: {r_issue.text}")
        print("Failed to fetch F20M-27:", r_issue.status_code)

# 2. Get all projects in Jira
r_projs = requests.get(f"{jira_url}/rest/api/3/project", auth=auth, timeout=10)
if r_projs.status_code == 200:
    jira_projects = r_projs.json()
    print(f"\nDiscovered {len(jira_projects)} Jira Projects:")
    for jp in jira_projects:
        print(f" - Key: {jp.get('key')} | Name: {jp.get('name')} | ID: {jp.get('id')}")
else:
    print("Failed to fetch Jira projects:", r_projs.status_code)
