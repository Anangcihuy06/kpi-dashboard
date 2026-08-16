import sys
sys.path.append('c:/Users/ATI-User/KPI-Dashboard/backend')
from database import SessionLocal
import models
from encrypt import decrypt_val
import requests

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()
jira_url = setting.jira_url.rstrip('/')
jira_token = decrypt_val(setting.jira_token_encrypted)
jira_auth = (setting.jira_email, jira_token)

for y in [2024, 2025, 2026]:
    payload = {
        'jql': f'worklogDate >= "{y}-01-01" AND worklogDate <= "{y}-12-31"',
        'maxResults': 1
    }
    resp = requests.post(f'{jira_url}/rest/api/3/search/jql', auth=jira_auth, json=payload)
    data = resp.json()
    print(f'Year {y} issues with worklog: {len(data.get("issues", []))} (isLast: {data.get("isLast")})')
