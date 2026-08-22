import requests
import json

url = "https://services-kpi-production.up.railway.app/api/v1/kpi/team-yearly?user_id=482&year=2026&direct_only=true"

while True:
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        for u in data['data']: print(u['full_name'], u['nik'])
        break
    import time
    time.sleep(1)
