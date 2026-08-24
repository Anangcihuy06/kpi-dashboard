import requests
import time
import sys

BASE_URL = "https://services-kpi-production.up.railway.app/api/v1"
print("Logging in...")
res = requests.post(f"{BASE_URL}/auth/login", json={
    "username": "01.05.13.500",
    "password": "rf1d"
})
if not res.ok:
    print("Login failed:", res.status_code)
    sys.exit(1)

token = res.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

print("Triggering full sync to apply the fix...")
res = requests.post(f"{BASE_URL}/sync/trigger", headers=headers)
if not res.ok:
    print("Sync failed to start:", res.text)
    sys.exit(1)

print("Sync triggered. Waiting 30 seconds for it to complete on Railway...")
time.sleep(30)

print("Fetching Nanang's updated score...")
res = requests.get(f"{BASE_URL}/kpi/team-yearly?user_id=482&year=2026&direct_only=true", headers=headers)
data = res.json()
nanang = next((u for u in data["users"] if "Nanang" in u.get("full_name", "")), None)
if nanang:
    print(f"Nanang's Score: {nanang['summary']['kpi_score']}")
    print(f"Nanang's Tickets: {nanang['summary']['total_issues_completed']}")
    print(f"Nanang's SP: {nanang['summary']['total_story_points']}")
else:
    print("Nanang not found")
