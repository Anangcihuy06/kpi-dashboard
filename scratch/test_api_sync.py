import requests

print("Triggering background sync for year 2026 for Nanang's team...")
# Nanang's user ID is api_6518
res = requests.post("http://127.0.0.1:8000/api/v1/attendance/sync-year?supervisor_id=api_6518&year=2026")
print(res.json())
