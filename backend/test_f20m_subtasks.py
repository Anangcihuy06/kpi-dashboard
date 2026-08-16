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

sub_keys = ["F20M-42", "F20M-43", "F20M-44", "F20M-45", "F20M-46", "F20M-47", "F20M-48", "F20M-49", "F20M-50", "F20M-51", "F20M-52", "F20M-53", "F20M-57", "F20M-67", "F20M-68", "F20M-70", "F20M-73", "F20M-74", "F20M-75", "F20M-76"]

total_sub_sp = 0
print("=== SUB-TASKS FOR F20M-27 ===")
for k in sub_keys:
    r = requests.get(f"{jira_url}/rest/api/3/issue/{k}", auth=auth, timeout=10)
    if r.status_code == 200:
        f = r.json().get("fields", {})
        summary = f.get("summary")
        status = f.get("status", {}).get("name")
        assignee = f.get("assignee", {}).get("displayName") if f.get("assignee") else "Unassigned"
        sp = f.get("customfield_10024") or f.get("customfield_10016") or f.get("customfield_10028") or f.get("story_points") or 0
        if sp is None:
            sp = 0
        total_sub_sp += sp
        print(f" - {k} ({status}) | Assignee: {assignee} | SP: {sp} | {summary}")

print(f"\nTOTAL SUBTASK STORY POINTS FOR F20M-27: {total_sub_sp}")
