import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime
from main import get_time_range_kpi, TimeRangeKPIRequest

db = SessionLocal()

from_date = "2026-01-01"
to_date = "2026-12-31"

all_active_users = db.query(models.User).filter(models.User.is_active == True).all()
uids = [u.id for u in all_active_users]

req = TimeRangeKPIRequest(from_date=from_date, to_date=to_date, user_ids=uids)
res = get_time_range_kpi(request=req, user_id='482', db=db)

users = res.get("users", [])

print("=== SIMULATION: 2-PILLAR BASELINE LEADERBOARD (90% Feature Complexity, 10% Attendance) ===")
print("Complexity Target: 300.0 Pts | Delivery Ticket Count: REMOVED COMPLETELY")
print("-" * 110)

target_complexity = 300.0

sim_results = []
for u in users:
    actual_complexity = u['kpi_scores']['details'][0]['actual_value']
    attendance_score = u['kpi_scores']['details'][3]['calculated_score'] if len(u['kpi_scores']['details']) > 3 else 0.0
    
    comp_score = min((actual_complexity / target_complexity) * 100.0, 100.0)
    
    final_score = comp_score * 0.90 + attendance_score * 0.10
    sim_results.append({
        "name": u["full_name"],
        "comp_score": comp_score,
        "attendance_score": attendance_score,
        "final_score": round(final_score, 2),
        "raw_feat": actual_complexity
    })

for i, s in enumerate(sorted(sim_results, key=lambda x: x["final_score"], reverse=True), start=1):
    print(f"#{i:<2} {s['name']:<30} | Feat Pts: {s['raw_feat']:<6.1f} | Feat Score: {s['comp_score']:<5.1f}% | Att: {s['attendance_score']:<5.1f}% | FINAL SCORE: {s['final_score']}")
