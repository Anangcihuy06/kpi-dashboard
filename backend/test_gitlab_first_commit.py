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

print(f"=== TESTING GITLAB INITIAL COMMIT SCAN FOR {len(projects)} PROJECTS ===")

founder_matches = []

for p in projects[:15]:
    pid = p.external_project_id
    if not pid:
        continue
    
    url = f"{gitlab_url}/api/v4/projects/{pid}/repository/commits"
    r = requests.get(url, headers=headers, params={"per_page": 1}, timeout=10)
    
    if r.status_code == 200:
        total_pages = r.headers.get("X-Total-Pages", "1")
        # Fetch last page to get initial commit
        r_first = requests.get(url, headers=headers, params={"per_page": 1, "page": total_pages}, timeout=10)
        if r_first.status_code == 200 and r_first.json():
            init_c = r_first.json()[0]
            author_name = init_c.get("author_name")
            author_email = init_c.get("author_email")
            created_at = init_c.get("committed_date")
            print(f"Project {p.project_name} (ID {pid}) -> Initial Commit on {created_at} by {author_name} <{author_email}>")
            
            # Match user
            for u in users:
                identities = db.query(models.EmployeeIdentity).filter(models.EmployeeIdentity.user_id == u.id).all()
                emails = [u.email] + [i.email for i in identities if i.email]
                names = [u.full_name] + [i.full_name for i in identities if i.full_name]
                unames = [i.username for i in identities if i.username]
                
                if (author_email and any(e and e.lower() == author_email.lower() for e in emails)) or \
                   (author_name and any(n and n.lower() in author_name.lower() or author_name.lower() in n.lower() for n in names)) or \
                   (author_name and any(un and un.lower() == author_name.lower() for un in unames)):
                    founder_matches.append((p.project_name, u.full_name, author_name, created_at))
                    print(f"   >>> MATCHED FOUNDER: {u.full_name}")
                    break

print(f"\nFOUND {len(founder_matches)} MATCHES IN TEST!")
