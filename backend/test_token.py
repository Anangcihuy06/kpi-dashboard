import sys
import os
sys.path.append(os.getcwd())
from sync_service import get_system_token, fetch_all_subordinates_attendance

token = get_system_token()
print(f"Token: {token[:10]}...")
if token:
    records = fetch_all_subordinates_attendance(token, 2026)
    print("Len records by NIK:", len(records))
    if records:
        print("Keys:", list(records.keys())[:5])
