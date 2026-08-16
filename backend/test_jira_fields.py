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

jql = 'assignee = "5de71ecb8743750d00b7fbf5"'

# Try GET /rest/api/3/search
r = requests.get(f"{jira_url}/rest/api/3/search", auth=auth, params={"jql": jql, "maxResults": 100}, timeout=15)
if r.status_code == 200:
    issues = r.json().get("issues", [])
    print(f"Standard /rest/api/3/search returned {len(issues)} issues")
    
    with open('c:/Users/ATI-User/KPI-Dashboard/backend/nanang_jira_issues.txt', 'w', encoding='utf-8') as f:
        f.write(f"Total Issues: {len(issues)}\n\n")
        for iss in issues:
            fields = iss.get('fields', {})
            key = iss.get('key')
            proj = fields.get('project', {})
            proj_key = proj.get('key') if proj else 'NO_KEY'
            proj_name = proj.get('name') if proj else 'NO_NAME'
            st = fields.get('status', {})
            st_name = st.get('name') if st else 'NO_ST'
            st_cat = st.get('statusCategory', {}).get('name') if st else 'NO_CAT'
            
            sp_24 = fields.get('customfield_10024')
            sp_16 = fields.get('customfield_10016')
            sp_28 = fields.get('customfield_10028')
            sp_val = sp_24 if sp_24 is not None else (sp_16 if sp_16 is not None else (sp_28 if sp_28 is not None else 0))
            
            summary = fields.get('summary', '')
            updated = fields.get('updated', '')
            f.write(f"{key} [{proj_key} - {proj_name}] ({st_name} / {st_cat}) | SP: {sp_val} (24:{sp_24}, 16:{sp_16}, 28:{sp_28}) | Updated: {updated} | {summary}\n")
    print("Written nanang_jira_issues.txt successfully!")
else:
    print("Failed /rest/api/3/search:", r.status_code, r.text)
