import requests
import json
from datetime import datetime

# Test direct HRIS API first
print("=== Testing HRIS API directly ===")

# Get HRIS token
hris_url = "https://talent-backend.andreasbilly.com/api/authenticate/mobile"
hris_payload = {
    "username": "01.05.13.500",
    "password": "rf1d"
}

try:
    print("Getting HRIS token...")
    hris_response = requests.post(hris_url, json=hris_payload, timeout=30)
    if hris_response.status_code == 200:
        token = hris_response.json().get("id_token")
        print(f"Token obtained: {token[:30]}...")
        
        # Test attendance API
        att_url = f"https://talent-backend.andreasbilly.com/api/app/users/attendances-new?page=0&size=10&startDate=2025-01-01&endDate=2025-12-31"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        print("Testing HRIS attendance API...")
        att_response = requests.get(att_url, headers=headers, timeout=10)
        if att_response.status_code == 200:
            data = att_response.json()
            print(f"HRIS API returned {len(data) if isinstance(data, list) else 'dict'} records")
            
            if len(data) > 0:
                print("Sample record:")
                print(json.dumps(data[0], indent=2))
        else:
            print(f"HRIS API failed: {att_response.status_code} - {att_response.text}")
    else:
        print(f"HRIS auth failed: {hris_response.status_code} - {hris_response.text}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Testing Production API ===")
# Now test our production API
try:
    # Check current attendance records
    att_url = "https://services-kpi-production.up.railway.app/api/v1/attendance/records?supervisor_id=482&year=2025"
    response = requests.get(att_url, timeout=10)
    data = response.json()
    print(f"Current attendance records in DB: {data.get('total_records')}")
    
    # Try to trigger sync with credentials
    sync_url = "https://services-kpi-production.up.railway.app/api/v1/sync/data"
    sync_payload = {
        "supervisor_id": "482",
        "year": "2025",
        "hris_username": "01.05.13.500",
        "hris_password": "rf1d"
    }
    
    print("Triggering sync with credentials...")
    sync_response = requests.post(sync_url, json=sync_payload, timeout=15)
    if sync_response.status_code == 200:
        result = sync_response.json()
        job_id = result.get("job_id")
        print(f"Sync job started: {job_id}")
    else:
        print(f"Sync failed: {sync_response.status_code} - {sync_response.text}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()