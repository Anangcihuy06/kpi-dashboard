import sys
import os
sys.path.append(os.getcwd())
from database import SessionLocal
import models
from sync_service import get_system_token, fetch_all_subordinates_attendance

db = SessionLocal()
token = get_system_token()
if not token:
    print("Failed to get system token")
    sys.exit(1)

records = fetch_all_subordinates_attendance(token, 2026)
print(f"Total NIKs fetched for 2026 with admin token: {len(records)}")
