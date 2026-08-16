import sys
import os
sys.path.append(os.getcwd())
from sync_service import get_system_token, fetch_all_subordinates_attendance
from database import SessionLocal
import models
from datetime import datetime

token = get_system_token()
records_by_nik = fetch_all_subordinates_attendance(token, 2026)
nanang_records = records_by_nik.get("01.04.19.1905", [])

lates = 0
for rec in nanang_records:
    remark = (rec.get("remarkText") or "").lower()
    if "late" in remark:
        lates += 1
        print("LATE:", rec.get("date"), remark)

print(f"Total lates: {lates}")
