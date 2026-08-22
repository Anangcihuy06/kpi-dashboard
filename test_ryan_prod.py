import requests
import time
import json
import urllib3

urllib3.disable_warnings()

BASE_URL = "https://services-kpi-production.up.railway.app/api/v1"

def login():
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "01.05.13.500",
        "password": "rf1d"
    })
    if not res.ok:
        print("Login failed:", res.text)
        return None, None
    data = res.json()
    token = data.get("token")
    user = data.get("user", {})
    return token, user

def poll_job(token, job_id, name):
    print(f"Polling {name} job: {job_id}")
    while True:
        res = requests.get(f"{BASE_URL}/jobs/{job_id}", headers={"Authorization": f"Bearer {token}"})
        if not res.ok:
            print("Failed to poll job:", res.text)
            return False
        st = res.json()
        print(f"{name} status:", st.get("status"), st.get("progress"), "%")
        if st.get("status") in ["COMPLETED", "FAILED"]:
            if st.get("status") == "FAILED":
                print("Job Failed:", st.get("error_message"))
                return False
            return True
        time.sleep(3)

def run():
    token, user = login()
    if not token:
        return
    
    user_id = user.get("id")
    print(f"Logged in as {user.get('full_name')} (ID: {user_id})")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("Triggering Sync Data...")
    res = requests.post(f"{BASE_URL}/sync/data?supervisor_id={user_id}", headers=headers)
    if not res.ok:
        print("Sync failed:", res.text)
        return
    sync_job_id = res.json().get("job_id")
    if not poll_job(token, sync_job_id, "Sync"):
        return
        
    print("Triggering KPI Calculation...")
    res = requests.post(f"{BASE_URL}/kpi/calculate/2026?force=true&supervisor_id={user_id}", headers=headers)
    if not res.ok:
        print("Calc failed:", res.text)
        return
    calc_job_id = res.json().get("job_id")
    if not poll_job(token, calc_job_id, "Calc"):
        return
        
    print("Fetching KPI...")
    res = requests.get(f"{BASE_URL}/kpi/yearly-performance?year=2026&user_id={user_id}", headers=headers)
    if not res.ok:
        print("Fetch failed:", res.text)
        return
    data = res.json().get("data", {})
    summary = data.get("summary", {})
    print("\n--- RESULTS ---")
    print(f"User: {user.get('full_name')}")
    print(f"Overall KPI: {summary.get('overall_score')}")
    print(f"Total Points: {summary.get('total_story_points_completed')}")
    print(f"Tasks Completed: {summary.get('total_tasks_completed')}")

if __name__ == "__main__":
    run()
