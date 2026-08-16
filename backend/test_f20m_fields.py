import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import requests
import json
import models
from database import SessionLocal
from encrypt import decrypt_val

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()

jira_url = setting.jira_url.rstrip('/')
jira_email = setting.jira_email
jira_token = decrypt_val(setting.jira_token_encrypted)
auth = (jira_email, jira_token)

# Fetch F20M-27
r = requests.get(f"{jira_url}/rest/api/3/issue/F20M-27", auth=auth, timeout=10)
if r.status_code == 200:
    issue_data = r.json()
    fields = issue_data.get("fields", {})
    
    with open('c:/Users/ATI-User/KPI-Dashboard/backend/f20m_fields_check.txt', 'w', encoding='utf-8') as f:
        f.write("=== NON-NULL FIELDS FOR F20M-27 ===\n")
        for k, v in fields.items():
            if v is not None and v != [] and v != {} and v != "":
                f.write(f"{k}: {v}\n")
    print("Written f20m_fields_check.txt!")
