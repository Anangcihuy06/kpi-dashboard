import requests
import time

url = "https://services-kpi-production.up.railway.app/api/v1/kpi/team-yearly?user_id=482&year=2026&direct_only=true"

while True:
    res = requests.get(url)
    print("Status:", res.status_code)
    if res.status_code == 200:
        data = res.json()
        if "data" in data and isinstance(data["data"], list):
            for user in data["data"]:
                name = user.get("full_name")
                att = user.get("summary", {}).get("total_attendance_days", 0)
                late_pct = user.get("summary", {}).get("total_late_count", 0)
                print(f"{name}: att={att}, late_count={late_pct}")
        else:
            print("Response:", data)
        break
    else:
        print("Waiting...")
        time.sleep(3)
