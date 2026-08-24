import requests
res = requests.get('https://services-kpi-production.up.railway.app/api/v1/kpi/yearly-performance?year=2026&user_id=1276')
data = res.json()
print("Yanes Arfian KPI =", data.get("data", {}).get("summary", {}).get("overall_score", 0))
print("Yanes Arfian Total Points =", data.get("data", {}).get("summary", {}).get("total_story_points_completed", 0))
