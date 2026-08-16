import requests
from database import SessionLocal
from models import IntegrationSetting
from comprehensive_sync import decrypt_val

db = SessionLocal()
settings = db.query(IntegrationSetting).first()
jira_token = decrypt_val(settings.jira_token_encrypted)
jira_auth = (settings.jira_email, jira_token)
jira_url = settings.jira_url.rstrip('/')

jql = 'assignee = "5de71ecb8743750d00b7fbf5" AND status CHANGED TO ("Ready for QA", "Ready for UAT", "Ready to Release", "Done") DURING ("2026-01-01", "2026-12-31")'
res = requests.get(f"{jira_url}/rest/api/3/search/jql", auth=jira_auth, params={"jql": jql, "maxResults": 10})
print(res.json())
