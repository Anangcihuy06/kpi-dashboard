import requests
import json

try:
    res = requests.get('http://localhost:8000/api/v1/kpi/yearly-performance?year=2026&user_id=6518')
    data = res.json()
    print("Final Score:", data.get('data', {}).get('final_score'))
except Exception as e:
    print("Error:", e)
