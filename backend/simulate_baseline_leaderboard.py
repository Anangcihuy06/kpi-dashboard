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

# Let's inspect the current values
users = res.get("users", [])

print("=== CURRENT RELATIVE LEADERSHIP (2026) ===")
for u in sorted(users, key=lambda x: x["final_score"], reverse=True):
    print(f"User: {u['full_name']:<30} | Raw Feat: {u['kpi_scores']['details'][0]['actual_value']:<6.1f} | Raw Tasks: {u['summary']['total_issues_completed']:<4} | Final Score: {u['final_score']}")

print("\n=== SIMULATION: FIXED YEARLY TARGET BASELINE (Target: 300 Pts, 40 Tasks) ===")
# We evaluate: score = min((actual / target) * 100, 100.0)
target_complexity = 300.0
target_tasks = 40.0

simulated_results = []
for u in users:
    actual_complexity = u['kpi_scores']['details'][0]['actual_value']
    actual_tasks = u['summary']['total_issues_completed']
    attendance_score = u['kpi_scores']['details'][3]['calculated_score'] if len(u['kpi_scores']['details']) > 3 else 0.0
    
    comp_score = min((actual_complexity / target_complexity) * 100.0, 100.0)
    task_score = min((actual_tasks / target_tasks) * 100.0, 100.0)
    
    final_score = comp_score * 0.60 + task_score * 0.30 + attendance_score * 0.10
    simulated_results.append({
        "name": u["full_name"],
        "comp_score": comp_score,
        "task_score": task_score,
        "attendance_score": attendance_score,
        "final_score": round(final_score, 2),
        "raw_feat": actual_complexity,
        "raw_tasks": actual_tasks
    })

for s in sorted(simulated_results, key=lambda x: x["final_score"], reverse=True):
    print(f"User: {s['name']:<30} | Feat Score: {s['comp_score']:<5.1f}% ({s['raw_feat']:.1f}) | Task Score: {s['task_score']:<5.1f}% ({s['raw_tasks']}) | Att: {s['attendance_score']:.1f}% | Final Score: {s['final_score']}")
