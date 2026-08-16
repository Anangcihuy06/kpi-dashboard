import requests
from database import SessionLocal
from models import IntegrationSetting
from comprehensive_sync import decrypt_val

db = SessionLocal()
settings = db.query(IntegrationSetting).first()
gitlab_url = settings.gitlab_url.rstrip('/')
gitlab_token = decrypt_val(settings.gitlab_token_encrypted)
headers = {'PRIVATE-TOKEN': gitlab_token}

r = requests.get(f'{gitlab_url}/api/v4/projects/415/repository/commits', headers=headers, params={'since': '2026-01-01T00:00:00Z', 'until': '2026-12-31T23:59:59Z', 'per_page': 50})
if r.status_code == 200:
    commits = r.json()
    for c in commits:
        if c.get('author_name') == 'Anangcihuy06':
            print(f'Email of Anangcihuy06: {c.get("author_email")}')
            break
