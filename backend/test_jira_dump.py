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

jql = 'assignee = "5de71ecb8743750d00b7fbf5"'
params = {
    "jql": jql,
    "maxResults": 50
}
r = requests.get(f"{jira_url}/rest/api/3/search/jql", auth=auth, params=params, timeout=15)
with open('c:/Users/ATI-User/KPI-Dashboard/backend/jira_sample_out.txt', 'w', encoding='utf-8') as f:
    f.write(f"Status: {r.status_code}\n")
    if r.status_code == 200:
        data = r.json()
        f.write(f"Issues count: {len(data.get('issues', []))}\n")
        f.write(json.dumps(data, indent=2))
    else:
        f.write(r.text)
