import sys
import os

# Ensure backend directory is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database import SessionLocal
import models
from main import get_time_range_kpi, TimeRangeKPIRequest
import json

def check_yanes():
    db = SessionLocal()
    
    # Get Yanes (ID 1276 or NIK 17.07.17.1150)
    yanes = db.query(models.User).filter(models.User.nik == '17.07.17.1150').first()
    if not yanes:
        yanes = db.query(models.User).filter(models.User.full_name.ilike('%yanes%')).first()
        
    if not yanes:
        print("Yanes not found")
        return
        
    print(f"Found Yanes: {yanes.full_name} (ID: {yanes.id})")
    
    subs = db.query(models.User).filter(models.User.supervisor_id == yanes.id).all()
    print(f"Found {len(subs)} direct subordinates:")
    
    sub_ids = [sub.id for sub in subs]
    
    if not sub_ids:
        print("No subordinates found.")
        return
        
    # Calc KPI for 2026
    req = TimeRangeKPIRequest(from_date="2026-01-01", to_date="2026-12-31", user_ids=sub_ids)
    res = get_time_range_kpi(req, yanes.id, db)
    
    if "users" in res:
        for u in res["users"]:
            # get real name from DB
            real_sub = db.query(models.User).filter(models.User.id == u["user_id"]).first()
            name = real_sub.full_name if real_sub else u.get("name", "Unknown")
            print(f"- {name} (ID: {u['user_id']})")
            print(f"  Final Score: {u.get('final_score')}")
            print(f"  KPI Scores: {json.dumps(u.get('kpi_scores', {}))}")
            print(f"  Summary: {json.dumps(u.get('summary', {}), indent=2)}")
    else:
        print("No users in KPI response", res)

if __name__ == "__main__":
    check_yanes()
