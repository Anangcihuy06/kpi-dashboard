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

jql = 'assignee = "5de71ecb8743750d00b7fbf5"'
r = requests.get(f"{jira_url}/rest/api/3/search/jql", auth=auth, params={"jql": jql, "maxResults": 100}, timeout=15)
print('Status:', r.status_code)
if r.status_code == 200:
    data = r.json()
    issues = data.get('issues', [])
    print('Issues count:', len(issues))
    proj_counts = {}
    for i in issues:
        if isinstance(i, dict) and i.get('key'):
            pkey = i.get('key').split('-')[0]
            proj_counts[pkey] = proj_counts.get(pkey, 0) + 1
        elif isinstance(i, str):
            pkey = i.split('-')[0]
            proj_counts[pkey] = proj_counts.get(pkey, 0) + 1
    
    with open('c:/Users/ATI-User/KPI-Dashboard/backend/nanang_projects.txt', 'w', encoding='utf-8') as f:
        f.write("Jira Projects assigned to Nanang:\n")
        for p, cnt in proj_counts.items():
            f.write(f" - {p}: {cnt} issues\n")
    print("Written nanang_projects.txt!")
else:
    print("Failed:", r.status_code, r.text)
