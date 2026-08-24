import requests
import time

url = "https://services-kpi-production.up.railway.app/api/v1/kpi/team-yearly?user_id=482&year=2026"
while True:
    resp = requests.get(url)
    data = resp.json()
    if data.get('status') == 'success':
        for user in data.get('data', []):
            if user.get('nik') in ['9030019']:
                print(f"Nanang's Division: {user.get('division_id')}, Group: {user.get('group_id')}")
        break
    time.sleep(2)
