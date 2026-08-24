import sys
sys.path.insert(0, 'backend')
import requests
from database import SessionLocal
from models import IntegrationSetting
from encrypt import decrypt_val
db = SessionLocal()
settings = db.query(IntegrationSetting).first()
token = decrypt_val(settings.jira_token_encrypted)
auth = (settings.jira_email, token)
res = requests.post(settings.jira_url.rstrip('/') + '/rest/api/3/search/jql', json={'jql': 'issue = KD-1', 'maxResults': 1, 'fields': ['status', 'resolutiondate']}, auth=auth)
data = res.json()
print(data)
