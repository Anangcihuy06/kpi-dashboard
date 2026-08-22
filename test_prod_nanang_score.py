import requests

BASE_URL = "https://services-kpi-production.up.railway.app/api/v1"

res = requests.post(f"{BASE_URL}/auth/login", json={
    "username": "01.05.13.500",
    "password": "rf1d"
})
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

res = requests.get(f"{BASE_URL}/kpi/team-yearly?user_id=482&year=2026&direct_only=true", headers=headers)
data = res.json()
nanang = next((u for u in data["users"] if u["user_id"] == 489), None)
if nanang:
    print(f"Nanang's Score: {nanang['summary']['kpi_score']}")
    print(f"Nanang's Tickets: {nanang['summary']['total_issues_completed']}")
    print(f"Nanang's SP: {nanang['summary']['total_story_points']}")
else:
    print("Nanang not found")
