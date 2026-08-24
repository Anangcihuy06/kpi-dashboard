import requests
import time
job_id = 'b665be70-72da-45da-9ee1-c449c6fb20a5'
url = f"https://services-kpi-production.up.railway.app/api/v1/jobs/{job_id}"
while True:
    response = requests.get(url)
    data = response.json()
    print("Status:", data.get('status'))
    if data.get('status') in ['COMPLETED', 'FAILED']:
        print("Data:", data)
        break
    time.sleep(2)
