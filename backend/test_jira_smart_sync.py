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

account_id = "5de71ecb8743750d00b7fbf5"  # Nanang

# JQL: all issues assigned to user updated in 2026
jql = f'assignee = "{account_id}" AND updated >= "2026-01-01" AND updated <= "2026-12-31"'
params = {
    "jql": jql,
    "fields": "summary,status,project,created,updated,resolutiondate,customfield_10024,customfield_10016,customfield_10028,story_points",
    "maxResults": 100
}

r = requests.get(f"{jira_url}/rest/api/3/search/jql", auth=auth, params=params, timeout=15)
if r.status_code == 200:
    data = r.json()
    issues = data.get("issues", [])
    print(f"Discovered {len(issues)} Jira issues for Nanang updated in 2026:")
    
    proj_map = {}
    total_sp = 0
    with open('c:/Users/ATI-User/KPI-Dashboard/backend/nanang_2026_jira.txt', 'w', encoding='utf-8') as f:
        for iss in issues:
            fields = iss.get("fields", {})
            key = iss.get("key")
            proj_info = fields.get("project", {})
            pkey = proj_info.get("key")
            pname = proj_info.get("name")
            status = fields.get("status", {}).get("name")
            st_cat = fields.get("status", {}).get("statusCategory", {}).get("name")
            
            # Story points check
            sp = fields.get("customfield_10024") or fields.get("customfield_10016") or fields.get("customfield_10028") or fields.get("story_points") or 0
            if sp is None:
                sp = 0
            
            total_sp += sp
            proj_map[pkey] = proj_map.get(pkey, 0) + 1
            f.write(f"{key} [{pkey} - {pname}] ({status} / {st_cat}) | SP: {sp} | Summary: {fields.get('summary')}\n")
            
    print("Project counts for Nanang in 2026:")
    for pk, count in proj_map.items():
        print(f" - Project Key {pk}: {count} issues")
    print(f"TOTAL STORY POINTS IN 2026: {total_sp}")
else:
    print("Failed JQL:", r.status_code, r.text)
