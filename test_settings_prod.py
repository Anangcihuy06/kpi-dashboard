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
    
    print("Fetching Settings...")
    res = requests.get(f"{BASE_URL}/sync/settings", headers=headers)
    if not res.ok:
        print("Fetch failed:", res.text)
        return
        
    data = res.json()
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    run()
