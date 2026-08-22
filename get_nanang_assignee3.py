import sys
sys.path.insert(0, 'backend')
import requests
from database import SessionLocal
from models import IntegrationSetting
db = SessionLocal()
settings = db.query(IntegrationSetting).first()
auth = (settings.jira_email, settings.get_decrypted_jira_token(db))
res = requests.get(settings.jira_url.rstrip('/') + '/rest/api/2/search', params={'jql': 'assignee = "nanang.wahyudi"', 'maxResults': 1}, auth=auth)
data = res.json()
if 'issues' in data and data['issues']:
    print("Found issue:", data['issues'][0]['key'])
    print("Assignee field:", data['issues'][0].get('fields', {}).get('assignee', {}))
else:
    print("No issues found or error:", data)
