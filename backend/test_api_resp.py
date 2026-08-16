import requests
import json

url = "http://127.0.0.1:8000/api/v1/kpi/yearly-performance?user_id=6518&year=2026"
res = requests.get(url)
print("Status:", res.status_code)
data = res.json()
print("Final Score:", data.get("data", {}).get("final_score"))
print("Summary:", json.dumps(data.get("data", {}).get("summary"), indent=2))
print("Projects:", json.dumps(data.get("data", {}).get("projects"), indent=2))
print("KPI Scores:", json.dumps(data.get("data", {}).get("kpi_scores"), indent=2))
