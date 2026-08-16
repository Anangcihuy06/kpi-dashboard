import requests
from database import SessionLocal
from models import IntegrationSetting
from comprehensive_sync import decrypt_val

db = SessionLocal()
settings = db.query(IntegrationSetting).first()
gitlab_url = settings.gitlab_url.rstrip('/')
gitlab_token = decrypt_val(settings.gitlab_token_encrypted)
headers = {'PRIVATE-TOKEN': gitlab_token}

# Get ALL projects accessible by Nanang (user id 9)
page = 1
all_projects = []
while True:
    res = requests.get(f'{gitlab_url}/api/v4/projects', headers=headers, params={
        'membership': True,
        'sudo': 'anang',
        'per_page': 100,
        'page': page
    })
    if res.status_code != 200:
        # Try without sudo
        res = requests.get(f'{gitlab_url}/api/v4/projects', headers=headers, params={
            'per_page': 100,
            'page': page
        })
    projects = res.json()
    if not projects:
        break
    all_projects.extend(projects)
    page += 1
    if page > 5:
        break

print(f"Total accessible projects: {len(all_projects)}")

# Check commits per project for Nanang
total = 0
for p in all_projects:
    pid = p['id']
    for author in ['Nanang wahyudi']:
        params = {'author': author, 'since': '2026-01-01T00:00:00Z', 'until': '2026-12-31T23:59:59Z', 'per_page': 100}
        r = requests.get(f'{gitlab_url}/api/v4/projects/{pid}/repository/commits', headers=headers, params=params)
        if r.status_code == 200:
            commits = r.json()
            if isinstance(commits, list) and len(commits) > 0:
                total += len(commits)
                print(f"  Project {pid} ({p['name']}): {len(commits)} commits")

print(f"\nTotal commits in 2026: {total}")
