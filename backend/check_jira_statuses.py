import os
import requests
import json
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
from models import EmployeeIdentity, IntegrationSetting

db = SessionLocal()
settings = db.query(IntegrationSetting).first()

if not settings or not settings.jira_url:
    print("No Jira settings")
    exit(1)

ident = db.query(EmployeeIdentity).filter(EmployeeIdentity.user_id == '6518', EmployeeIdentity.source == 'jira').first()
if not ident:
    print("No Jira identity for Nanang")
    exit(1)

from encrypt import decrypt_val
token = decrypt_val(settings.jira_token_encrypted)

jql = f"assignee = '{ident.external_user_id}' ORDER BY updated DESC"
auth = (settings.jira_email, token)
url = f"{settings.jira_url.rstrip('/')}/rest/api/2/search"

try:
    res = requests.get(url, params={"jql": jql, "maxResults": 100}, auth=auth)
    data = res.json()
    print("JQL:", jql)
    print("Fetched issues:", len(data.get("issues", [])))
    for issue in data.get("issues", []):
        fields = issue.get("fields", {})
        status = fields.get("status", {}).get("name")
        res_date = fields.get("resolutiondate")
        print(f"Key: {issue.get('key')}, Status: {status}, ResDate: {res_date}")
except Exception as e:
    print("Error:", e)
