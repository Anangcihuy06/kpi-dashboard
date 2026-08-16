import sys
import os
sys.path.append(os.getcwd())
from sync_service import get_system_token, fetch_all_subordinates_attendance

token = get_system_token()
if not token:
    print("Failed to get token")
    sys.exit(1)

records_by_nik = fetch_all_subordinates_attendance(token, 2026)
nanang_nik = "01.04.19.1905"
records = records_by_nik.get(nanang_nik, [])

present_count = 0
late_count = 0

for rec in records:
    clock_in = rec.get("clockIn") or rec.get("clockin_time")
    if not clock_in:
        continue
    
    present_count += 1
    remark = (rec.get("remarkText") or "").lower()
    if "late" in remark:
        late_count += 1

print(f"Nanang (NIK {nanang_nik}) Attendance YTD 2026:")
print(f"Total Clock-ins (Present): {present_count}")
print(f"Late Count: {late_count}")
