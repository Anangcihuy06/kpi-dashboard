import requests
from database import SessionLocal
import models
from encryption import decrypt_val

db = SessionLocal()
settings = db.query(models.IntegrationSetting).first()
jira_token = decrypt_val(settings.jira_api_token_encrypted)
jira_url = settings.jira_url.rstrip('/')
email = settings.jira_email

auth = (email, jira_token)
url = f"{jira_url}/rest/api/3/search"
params = {
    'jql': 'worklogAuthor = "5de71ecb8743750d00b7fbf5"',
    'fields': 'worklog',
    'maxResults': 10
}
res = requests.get(url, auth=auth, params=params)
if res.status_code == 200:
    data = res.json()
    print(f"Total issues with worklogs by Nanang: {data.get('total')}")
else:
    print(res.status_code, res.text)
