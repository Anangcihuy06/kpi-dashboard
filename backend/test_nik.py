import sys
import os
sys.path.append(os.getcwd())
from sync_service import get_system_token, fetch_all_subordinates_attendance

token = get_system_token()
records_by_nik = fetch_all_subordinates_attendance(token, 2026)
print("Keys in records_by_nik:", list(records_by_nik.keys()))
