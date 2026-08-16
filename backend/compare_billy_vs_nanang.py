import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal
from datetime import datetime
from main import get_time_range_kpi, TimeRangeKPIRequest

db = SessionLocal()

print("=== COMPARING BILLY VS NANANG UNDER AUTOMATED MULTI-FACTOR ENGINE ===")

for year in [2025, 2026]:
    from_date = f"{year}-01-01"
    to_date = f"{year}-12-31"
    
    req = TimeRangeKPIRequest(from_date=from_date, to_date=to_date, user_ids=['9615', '6518'])  # Billy and Nanang
    res = get_time_range_kpi(request=req, user_id='482', db=db)  # Ryan as admin
    
    print(f"\nYEAR: {year}:")
    for u in res.get("users", []):
        print(f"User: {u['full_name']}")
        print(f"   - Total Completed Tasks: {u['summary']['total_issues_completed']}")
        # Raw complexity pts is raw complexity_sp
        raw_complexity = u['kpi_scores']['details'][0]['actual_value']
        print(f"   - Feature Complexity Points: {raw_complexity}")
        print(f"   - Standalone Founder Projects: {len(u['summary'].get('founder_projects', []))} projects")
        print(f"   - Attendance Score: {u['kpi_scores']['details'][3]['calculated_score'] if len(u['kpi_scores']['details']) > 3 else 0.0}%")
        print(f"   - FINAL PERFORMANCE KPI SCORE: {u['final_score']} / 100")
        print("   - Breakdown Matrix Pillars:")
        for det in u['kpi_scores']['details']:
            print(f"      + {det['label']}: Actual={det['actual_value']}, Benchmark={det['variables']}, Score={det['calculated_score']}, Weight={det['weight']*100}%, Weighted Score={det['weighted_score']}")
