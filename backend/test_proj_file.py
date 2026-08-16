import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import requests
import models
from database import SessionLocal
from encrypt import decrypt_val

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()
gitlab_url = setting.gitlab_url.rstrip('/')
gitlab_token = decrypt_val(setting.gitlab_token_encrypted)

headers = {'PRIVATE-TOKEN': gitlab_token}

print(f"GitLab URL: {gitlab_url}")

# Fetch ALL groups
r_groups = requests.get(f"{gitlab_url}/api/v4/groups", headers=headers, params={"all_available": True, "per_page": 100})
if r_groups.status_code == 200:
    groups = r_groups.json()
    print(f"Total GitLab Groups discovered: {len(groups)}")
    for g in groups:
        print(f" - Group: {g['full_path']} (ID: {g['id']})")

# Fetch ALL projects across instance
page = 1
all_projs = []
while page <= 10:
    r_projs = requests.get(f"{gitlab_url}/api/v4/projects", headers=headers, params={"all_available": True, "per_page": 100, "page": page})
    if r_projs.status_code == 200:
        batch = r_projs.json()
        if not batch:
            break
        all_projs.extend(batch)
        page += 1
    else:
        break

print(f"\nTOTAL DISCOVERED PROJECTS ACROSS ALL GROUPS & USERS: {len(all_projs)}")
with open('c:/Users/ATI-User/KPI-Dashboard/backend/projs.txt', 'w', encoding='utf-8') as f:
    f.write(f"Total Discovered Projects: {len(all_projs)}\n\n")
    for p in all_projs:
        f.write(f"ID {p['id']}: {p['path_with_namespace']} | {p['web_url']}\n")

print("Written all projects to projs.txt!")
