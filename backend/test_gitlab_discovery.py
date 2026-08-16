import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from config import settings
from encrypt import decrypt_val

gitlab_url = settings.gitlab_url.rstrip("/")
gitlab_token = decrypt_val(settings.gitlab_token_encrypted)
headers = {"PRIVATE-TOKEN": gitlab_token}

print(f"GitLab URL: {gitlab_url}")

# 1. Fetch all groups
print("\n--- GROUPS DISCOVERY ---")
r_groups = requests.get(f"{gitlab_url}/api/v4/groups", headers=headers, params={"all_available": True, "per_page": 100})
if r_groups.status_code == 200:
    groups = r_groups.json()
    print(f"Found {len(groups)} groups:")
    for g in groups:
        print(f" Group ID {g['id']}: {g['full_path']} ({g['name']})")
else:
    print("Failed groups:", r_groups.status_code, r_groups.text)

# 2. Fetch all projects (with pagination)
print("\n--- ALL PROJECTS DISCOVERY ---")
all_projects = []
page = 1
while True:
    r_proj = requests.get(f"{gitlab_url}/api/v4/projects", headers=headers, params={"all_available": True, "per_page": 100, "page": page})
    if r_proj.status_code == 200:
        batch = r_proj.json()
        if not batch:
            break
        all_projects.extend(batch)
        page += 1
        if page > 10:  # safety cap for testing
            break
    else:
        print(f"Failed page {page}: {r_proj.status_code}")
        break

print(f"Found {len(all_projects)} TOTAL projects across the entire GitLab server!")
for p in all_projects[:25]:
    print(f" Project ID {p['id']}: {p['path_with_namespace']} ({p['name']})")

if len(all_projects) > 25:
    print(f"... and {len(all_projects) - 25} more projects!")
