import requests
import json
url = "https://services-kpi-production.up.railway.app/api/v1/kpi/team-yearly?user_id=482&year=2026&direct_only=false"
response = requests.get(url)
print("Status:", response.status_code)
if response.status_code == 200:
    data = response.json()
    if 'data' in data:
        for u in data['data']:
            print(f"User {u.get('user_id')}: Attendance {u.get('summary', {}).get('total_attendance_days')}")
