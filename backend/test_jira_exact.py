import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import requests, json, models
from database import SessionLocal
from encrypt import decrypt_val

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()

jira_url = setting.jira_url.rstrip('/')
auth = (setting.jira_email, decrypt_val(setting.jira_token_encrypted))

url = "https://atibusinessgroup.atlassian.net/rest/api/3/search/jql?jql=assignee+%3D+%225de71ecb8743750d00b7fbf5%22+AND+updated+%3E%3D+%222026-01-01%22+AND+updated+%3C%3D+%222026-12-31%22&fields=summary%2Cdescription%2Csubtasks%2Cstatus%2Cproject%2Cissuetype%2Cpriority%2Cstory_points%2Ccustomfield_10024%2Ccustomfield_10016%2Ccustomfield_10028%2Cresolutiondate%2Ccreated%2Cupdated&maxResults=100"

r1 = requests.get(url, auth=auth)
data = r1.json()
print("GET with exact PROD string", r1.status_code, "total=", data.get('total'), "issues len=", len(data.get('issues', [])))
