import requests
from backend.database import SessionLocal
from backend.models import IntegrationSetting
db = SessionLocal()
settings = db.query(IntegrationSetting).first()
auth = (settings.jira_email, settings.get_decrypted_jira_token())
res = requests.get(settings.jira_url.rstrip('/') + '/rest/api/2/search', params={'jql': 'assignee = "nanang.wahyudi"', 'maxResults': 1}, auth=auth)
data = res.json()
if 'issues' in data and data['issues']:
    print(data['issues'][0].get('fields', {}).get('assignee', {}))
else:
    print("No issues found or error:", data)
