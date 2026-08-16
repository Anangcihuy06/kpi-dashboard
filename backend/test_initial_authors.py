import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import requests
import json
import models
from database import SessionLocal
from encrypt import decrypt_val

db = SessionLocal()
setting = db.query(models.IntegrationSetting).first()

gitlab_url = setting.gitlab_url.rstrip('/')
gitlab_token = decrypt_val(setting.gitlab_token_encrypted)
headers = {"PRIVATE-TOKEN": gitlab_token}

projects_to_check = [
    ("435", "falcon-v2/falcon-talent"),
    ("267", "falcon-v2/falcon-candidate-frontend")
]

for pid, pname in projects_to_check:
    print(f"=== FETCHING ORIGINAL INITIAL COMMITS FOR {pname} (ID {pid}) ===")
    
    # Get project details from GitLab API
    r_proj = requests.get(f"{gitlab_url}/api/v4/projects/{pid}", headers=headers, timeout=10)
    if r_proj.status_code == 200:
        pdata = r_proj.json()
        creator = pdata.get("creator_id")
        created_at = pdata.get("created_at")
        print(f"   Project Created At: {created_at} | Creator ID: {creator}")
    
    # Get earliest commits without date filter (order by default is reverse, so order=asc gives initial commits!)
    r_commits = requests.get(f"{gitlab_url}/api/v4/projects/{pid}/repository/commits", headers=headers, params={"all": True, "order": "asc", "per_page": 20}, timeout=15)
    if r_commits.status_code == 200:
        commits = r_commits.json()
        print(f"   Total initial commits fetched: {len(commits)}")
        for c in commits[:5]:
            print(f"    - [{c.get('committed_date')}] Author: {c.get('author_name')} <{c.get('author_email')}> | {c.get('title')}")
    else:
        print(f"   Failed commits: {r_commits.status_code}")
