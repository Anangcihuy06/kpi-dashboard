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
    
    # We found Nanang's ID was probably 6518 from previous transcript
    nanang_id = "6518"
    
    print(f"Fetching calc details for Nanang ({nanang_id})...")
    res = requests.get(f"{BASE_URL}/kpi/user-calculation-details?user_id={nanang_id}&year=2026", headers=headers)
    if res.ok:
        data = res.json()
        print("Detail fetched successfully.")
        
        yearly = data.get("yearly_summary", {})
        print(f"Score: {yearly.get('overall_score')}, SP: {yearly.get('jira_sp')}, Issues: {yearly.get('jira_issues_completed')}")
        
    else:
        print("Fetch failed:", res.text)
        
if __name__ == "__main__":
    run()
