import requests
url = 'https://services-kpi-production.up.railway.app/api/v1/kpi/team-yearly?user_id=482&year=2026'
while True:
    d = requests.get(url).json()
    if d.get('status') == 'success':
        for u in d.get('data', []):
            if u.get('full_name') == 'Nanang Wahyudi':
                print(f"Div: {u.get('division_id')} Grp: {u.get('group_id')} NIK: {u.get('nik')}")
        break
