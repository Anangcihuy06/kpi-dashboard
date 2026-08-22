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
    
    # We can fetch the raw activities?
    res = requests.get(f"{BASE_URL}/kpi/activities?user_id=6518&from_date=2026-08-01&to_date=2026-08-31", headers=headers)
    print(res.status_code)
    # The activities endpoint had a 500 error because of `isoformat` on `activity_date=None`.
    # BUT wait, the `activity_date` cannot be None if we fallback to datetime.now().date().
    # Let me check the activities for the whole year to see if any are returned.
    
    # Actually, we can use an arbitrary query via test_nanang_prod.py if we had an endpoint.
    # Since we can't query SQLite directly on Railway, and `activities` throws 500...
    pass

if __name__ == "__main__":
    run()
