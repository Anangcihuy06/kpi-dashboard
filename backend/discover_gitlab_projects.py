import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
from config import settings
from encrypt import decrypt_val

token = decrypt_val(settings.gitlab_token_encrypted)
url = settings.gitlab_url.rstrip('/') + '/api/v4'
headers = {'PRIVATE-TOKEN': token}

print("Fetching GitLab Groups...")
r_groups = requests.get(f'{url}/groups', headers=headers, params={'all_available': True, 'per_page': 100}, timeout=10)
if r_groups.status_code == 200:
    groups = r_groups.json()
    print(f"Groups count: {len(groups)}")
    for g in groups:
        print(f" Group ID {g['id']}: {g['full_path']}")

print("\nFetching All Projects Across Instance...")
page = 1
all_projs = []
while page <= 10:
    r_projs = requests.get(f'{url}/projects', headers=headers, params={'all_available': True, 'per_page': 100, 'page': page}, timeout=10)
    if r_projs.status_code == 200:
        batch = r_projs.json()
        if not batch:
            break
        all_projs.extend(batch)
        print(f"Page {page}: fetched {len(batch)} projects (Total so far: {len(all_projs)})")
        page += 1
    else:
        print(f"Failed page {page}: {r_projs.status_code}")
        break

print(f"\nTOTAL PROJECTS FOUND: {len(all_projs)}")
print("Sample Projects (first 20):")
for p in all_projs[:20]:
    print(f" - Project ID {p['id']}: {p['path_with_namespace']}")
