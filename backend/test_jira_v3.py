import sys
sys.path.append('c:/Users/ATI-User/KPI-Dashboard/backend')
from database import SessionLocal
import models
from encrypt import decrypt_val
import requests
import json

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()
jira_url = setting.jira_url.rstrip('/')
jira_token = decrypt_val(setting.jira_token_encrypted)
jira_auth = (setting.jira_email, jira_token)
account_id = '63bbbbfa50b9490924dc02d0'

payload = {
    'jql': f'worklogAuthor = "{account_id}"',
    'maxResults': 5,
    'fields': ['worklog', 'summary']
}
resp = requests.post(f'{jira_url}/rest/api/3/search/jql', auth=jira_auth, json=payload)
if resp.status_code == 200:
    data = resp.json()
    print('Total issues:', data.get('total'))
    if data.get('issues'):
        print('First issue fields:', json.dumps(data.get('issues')[0], indent=2))
    else:
        print('No issues found')
else:
    print('Error:', resp.text)
