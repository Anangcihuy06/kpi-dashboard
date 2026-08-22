import requests
import json
import urllib3

urllib3.disable_warnings()

BASE_URL = "https://services-kpi-production.up.railway.app/api/v1"

def run():
    # Use the DB diagnostics / query endpoint if it exists?
    # No, there is no arbitrary query endpoint. We can only use existing API.
    # Let's hit the login endpoint
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "01.05.13.500",
        "password": "rf1d"
    })
    token = res.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # We can fetch the raw activities?
    # Wait, /api/v1/kpi/activities gave 500 error! Let's debug why it gave 500!
    # "start_date = datetime.strptime(from_date, "%Y-%m-%d")"
    res = requests.get(f"{BASE_URL}/kpi/activities?user_id=6518&from_date=2026-08-20&to_date=2026-08-22", headers=headers)
    print(res.status_code)
    print(res.text)

if __name__ == "__main__":
    run()
