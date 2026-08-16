import requests
import json

try:
    res = requests.get('http://localhost:8000/api/v1/kpi/yearly-performance?year=2026&user_id=6518')
    data = res.json()
    print(json.dumps(data.get('data', {}).get('details', []), indent=2))
except Exception as e:
    print("Error:", e)
