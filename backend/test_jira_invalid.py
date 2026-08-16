import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import requests, models
from database import SessionLocal
from encrypt import decrypt_val

db = SessionLocal()
s = db.query(models.IntegrationSetting).first()
auth = (s.jira_email, decrypt_val(s.jira_token_encrypted))
jql = 'assignee="jira_user_api_6518"'
params = {'jql': jql, 'maxResults': 5, 'fields': 'summary'}
r = requests.get(f"{s.jira_url.rstrip('/')}/rest/api/3/search/jql", auth=auth, params=params)
print(r.status_code, r.text)
