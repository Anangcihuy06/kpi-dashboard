import requests
import json

print("=== CHECKING LATE COUNTS & ATTENDANCE IN API (2026) ===")

r = requests.get('http://localhost:8000/api/v1/kpi/team-yearly?user_id=482&year=2026')
if r.status_code == 200:
    team_data = r.json().get('data', [])
    for member in team_data:
        uid = member.get('user_id')
        name = member.get('full_name')
        summary = member.get('summary', {})
        att = summary.get('total_attendance_days', 0)
        late = summary.get('total_late_count', 0)
        late_pct = round((late / att * 100) if att > 0 else 0, 2)
        print(f"User {uid} ({name}): Attendance Days = {att} | Late Count = {late} ({late_pct}% late)")
