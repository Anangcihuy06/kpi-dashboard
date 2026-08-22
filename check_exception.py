import sys
sys.path.insert(0, './backend')
from database import SessionLocal
import models
from main import get_time_range_kpi, TimeRangeKPIRequest
import traceback

def test():
    db = SessionLocal()
    try:
        user_id = "482"
        # Get subordinates of 482
        subordinates = db.query(models.User).filter(models.User.supervisor_id == user_id, models.User.is_active == True).all()
        target_ids = [s.id for s in subordinates]
        print("Target IDs:", target_ids)
        req = TimeRangeKPIRequest(from_date="2026-01-01", to_date="2026-12-31", user_ids=target_ids)
        res = get_time_range_kpi(request=req, user_id=user_id, db=db)
        print("Success, returned", len(res.get("users", [])), "users")
    except Exception as e:
        print("Exception:", e)
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test()
