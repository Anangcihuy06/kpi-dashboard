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
    
    print("Fetching summary for Nanang (6518)...")
    res = requests.get(f"{BASE_URL}/kpi/summary?user_id=6518&year=2026", headers=headers)
    if res.ok:
        data = res.json()
        print("Summary fetched successfully.")
        print("Overall Score:", data.get("yearly_stats", {}).get("overall_score"))
        print("Total Jira Issues:", data.get("yearly_stats", {}).get("total_issues"))
        print("Issues detail:", json.dumps(data.get("yearly_stats", {}).get("top_issues", [])[:5], indent=2))
        
    else:
        print("Summary fetch failed:", res.text)
        
if __name__ == "__main__":
    run()
