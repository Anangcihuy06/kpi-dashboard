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

projects = db.query(models.Project).all()
users = db.query(models.User).filter(models.User.is_active == True).all()

founder_registry = []

for p in projects:
    pid = p.external_project_id
    pname = p.project_name
    
    if not pid:
        continue
        
    url = f"{gitlab_url}/api/v4/projects/{pid}/repository/commits"
    try:
        r = requests.get(url, headers=headers, params={"per_page": 1}, timeout=5)
        if r.status_code == 200:
            total_pages = r.headers.get("X-Total-Pages", "1")
            r_first = requests.get(url, headers=headers, params={"per_page": 1, "page": total_pages}, timeout=5)
            
            if r_first.status_code == 200 and r_first.json():
                init_c = r_first.json()[0]
                author_name = init_c.get("author_name", "")
                author_email = init_c.get("author_email", "")
                committed_date = init_c.get("committed_date", "")
                
                matched_user = None
                for u in users:
                    identities = db.query(models.EmployeeIdentity).filter(models.EmployeeIdentity.user_id == u.id).all()
                    emails = [u.email] + [i.email for i in identities if i.email]
                    names = [u.full_name] + [i.full_name for i in identities if i.full_name]
                    unames = [i.username for i in identities if i.username]
                    
                    if (author_email and any(e and e.lower() == author_email.lower() for e in emails)) or \
                       (author_name and any(n and n.lower() in author_name.lower() or author_name.lower() in n.lower() for n in names)) or \
                       (author_name and any(un and un.lower() == author_name.lower() for un in unames)):
                        matched_user = u
                        break
                
                if matched_user:
                    founder_info = {
                        "project_id": p.id,
                        "external_project_id": pid,
                        "project_name": pname,
                        "founder_user_id": matched_user.id,
                        "founder_name": matched_user.full_name,
                        "initial_commit_date": committed_date,
                        "author_name": author_name,
                        "author_email": author_email,
                        "sp_credit": 150.0
                    }
                    founder_registry.append(founder_info)
    except Exception:
        pass

with open('c:/Users/ATI-User/KPI-Dashboard/backend/autodetected_founders.json', 'w', encoding='utf-8') as f:
    f.write(json.dumps(founder_registry, indent=2))

print(f"SUCCESSFULLY AUTODETECTED {len(founder_registry)} FOUNDERS!")
