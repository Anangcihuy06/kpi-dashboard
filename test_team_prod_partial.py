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
    user_id = "482"
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("Fetching Team KPI (Partial)...")
    url = f"{BASE_URL}/kpi/team-yearly?year=2026&user_id={user_id}&force_refresh=false"
    
    res = requests.get(url, headers=headers)
    if not res.ok:
        print("Fetch failed:", res.text)
        return
        
    data = res.json()
    
    if isinstance(data, dict):
        status = data.get("status")
        print(f"Job Status: {status}")
        results = data.get("data", [])
    elif isinstance(data, list):
        results = data
    else:
        print("Unknown format:", data)
        return
        
    print(f"\n--- RESULTS FOR {len(results)} SUBORDINATES (Partial/Completed) ---")
    for sub in results[:10]: # Print top 10
        print(f"\nUser: {sub.get('full_name')} (ID: {sub.get('user_id')})")
        print(f"Role: {sub.get('roles')}")
        summary = sub.get("summary", {})
        print(f"Overall KPI: {sub.get('final_score')}")
        print(f"Total Points: {summary.get('total_story_points')}")
        print(f"Tasks Completed: {summary.get('total_issues_completed')}")
        
    if len(results) > 10:
        print(f"\n... and {len(results) - 10} more.")

if __name__ == "__main__":
    run()
