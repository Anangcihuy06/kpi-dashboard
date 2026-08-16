import requests
from database import SessionLocal
from models import IntegrationSetting
from comprehensive_sync import decrypt_val

db = SessionLocal()
settings = db.query(IntegrationSetting).first()
gitlab_url = settings.gitlab_url.rstrip('/')
gitlab_token = decrypt_val(settings.gitlab_token_encrypted)
headers = {'PRIVATE-TOKEN': gitlab_token}

params1 = {'author': 'Nanang Wahyudi', 'since': '2026-01-01', 'until': '2026-12-31'}
res1 = requests.get(gitlab_url + '/api/v4/projects/445/repository/commits', headers=headers, params=params1)
print('Search with Nanang Wahyudi:', len(res1.json()) if isinstance(res1.json(), list) else res1.json())

params2 = {'author': 'Nanang wahyudi', 'since': '2026-01-01', 'until': '2026-12-31'}
res2 = requests.get(gitlab_url + '/api/v4/projects/445/repository/commits', headers=headers, params=params2)
print('Search with Nanang wahyudi:', len(res2.json()) if isinstance(res2.json(), list) else res2.json())
