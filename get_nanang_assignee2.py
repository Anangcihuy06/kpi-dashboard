import sys
sys.path.insert(0, 'backend')
import requests
from database import SessionLocal
from models import IntegrationSetting
db = SessionLocal()
settings = db.query(IntegrationSetting).first()
auth = (settings.jira_email, settings.get_decrypted_jira_token())
res = requests.get(settings.jira_url.rstrip('/') + '/rest/api/2/search', params={'jql': 'assignee = "nanang.wahyudi"', 'maxResults': 1}, auth=auth)
print(res.json().get('issues', [{}])[0].get('fields', {}).get('assignee', {}))
