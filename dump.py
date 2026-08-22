import requests
import json
res = requests.post('https://services-kpi-production.up.railway.app/api/v1/auth/login', json={'username':'01.05.13.500', 'password':'rf1d'})
token = res.json()['token']
data = requests.get('https://services-kpi-production.up.railway.app/api/v1/kpi/team-yearly?user_id=482&year=2026&direct_only=true', headers={'Authorization': 'Bearer ' + token}).json()
with open('temp.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
