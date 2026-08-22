import requests
url = "https://services-kpi-production.up.railway.app/api/v1/attendance/sync-year?supervisor_id=482&year=2026"
response = requests.post(url)
print("Status Code:", response.status_code)
print("Response:", response.json())
