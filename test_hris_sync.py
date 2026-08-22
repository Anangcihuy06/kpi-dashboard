import requests
import json
from datetime import datetime

# Test direct attendance sync with credentials
url = "https://services-kpi-production.up.railway.app/api/v1/sync/data"
payload = {
    "supervisor_id": "482",
    "year": "2025",
    "hris_username": "01.05.13.500",
    "hris_password": "rf1d"
}

print("Testing attendance sync with credentials override...")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload, timeout=15)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        job_id = data.get("job_id")
        print(f"Job ID: {job_id}")
        
        # Poll job status
        import time
        for i in range(12):  # 2 minutes
            time.sleep(10)
            try:
                job_response = requests.get(f"https://services-kpi-production.up.railway.app/api/v1/jobs/{job_id}")
                job_data = job_response.json()
                print(f"Progress: {job_data.get('progress')}%, Status: {job_data.get('status')}")
                
                if job_data.get('status') == 'COMPLETED':
                    print(f"Job completed! Result: {job_data.get('result')}")
                    break
                elif job_data.get('status') == 'FAILED':
                    print(f"Job failed! Error: {job_data.get('error_message')}")
                    break
            except Exception as e:
                print(f"Error checking job status: {e}")
        
        # Check attendance records
        time.sleep(5)
        att_response = requests.get("https://services-kpi-production.up.railway.app/api/v1/attendance/records?supervisor_id=482&year=2025")
        att_data = att_response.json()
        print(f"\nAttendance records after sync: {att_data.get('total_records')} records")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()