import requests
import json
import urllib3
import time

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
    
    print("Fetching Team KPI...")
    url = f"{BASE_URL}/kpi/team-yearly?year=2026&user_id={user_id}&force_refresh=true"
    
    while True:
        res = requests.get(url, headers=headers)
        if not res.ok:
            print("Fetch failed:", res.text)
            return
            
        data = res.json()
        if res.status_code == 202 or (isinstance(data, dict) and data.get("status") == "processing"):
            print("Job processing...")
            time.sleep(2)
        else:
            break
    
    if isinstance(data, dict) and data.get("status") == "success":
        results = data.get("data", [])
    elif isinstance(data, list):
        results = data
    else:
        print("Unknown format:", data)
        return
        
    print(f"\n--- RESULTS FOR {len(results)} SUBORDINATES ---")
    for sub in results:
        print(f"\nUser: {sub.get('full_name')} (ID: {sub.get('user_id')})")
        print(f"Role: {sub.get('roles')}")
        summary = sub.get("summary", {})
        print(f"Overall KPI: {sub.get('final_score')}")
        print(f"Total Points: {summary.get('total_story_points')}")
        print(f"Tasks Completed: {summary.get('total_issues_completed')}")

if __name__ == "__main__":
    run()
