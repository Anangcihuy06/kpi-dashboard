import requests
import json
import urllib3

urllib3.disable_warnings()

BASE_URL = "https://services-kpi-production.up.railway.app/api/v1"

def login():
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "01.05.13.500",
        "password": "rf1d"
    })
    return res.json().get("token")

def run():
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    
    print("Fetching team yearly for Ryan...")
    res = requests.get(f"{BASE_URL}/kpi/team-yearly?user_id=482&year=2026&direct_only=true", headers=headers)
    if not res.ok:
        print("Fetch failed:", res.text)
        return
        
    data = res.json()
    members = data.get("team_members", [])
    nanang = next((m for m in members if "Nanang" in m.get("user_name", "")), None)
    
    if not nanang:
        print("Nanang not found in team")
        return
        
    print(f"Nanang ID: {nanang['user_id']}, Score: {nanang['overall_score']}")
    print(f"Total SP: {nanang.get('total_story_points')}, Total Issues: {nanang.get('total_issues')}")
    
    print("Fetching activities for Nanang...")
    # There might be an endpoint to fetch activities or raw issues.
    # Let's try /api/v1/users/{nanang_id}/activities
    # or /api/v1/kpi/summary with user_id
    
    res = requests.get(f"{BASE_URL}/kpi/summary?user_id={nanang['user_id']}&year=2026", headers=headers)
    if res.ok:
        print("Summary keys:", res.json().keys())
        
if __name__ == "__main__":
    run()
