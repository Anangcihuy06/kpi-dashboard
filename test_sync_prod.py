import requests
import time
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
    
    print("Triggering sync...")
    res = requests.post(f"{BASE_URL}/attendance/sync-year?supervisor_id=482&year=2026", headers=headers)
    if not res.ok:
        print("Sync trigger failed:", res.text)
        return
        
    data = res.json()
    job_id = data.get("job_id")
    print(f"Job triggered: {job_id}")
    
    if job_id:
        while True:
            status_res = requests.get(f"{BASE_URL}/jobs/{job_id}", headers=headers)
            if not status_res.ok:
                print("Status check failed:", status_res.text)
                break
            status_data = status_res.json()
            print(f"Status: {status_data.get('status')}")
            if status_data.get('status') in ['COMPLETED', 'FAILED']:
                print(status_data)
                break
            time.sleep(2)
            
if __name__ == "__main__":
    run()
