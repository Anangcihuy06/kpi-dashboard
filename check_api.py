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
        req = TimeRangeKPIRequest(from_date="2026-01-01", to_date="2026-12-31", user_ids=[user_id])
        res = get_time_range_kpi(request=req, user_id=user_id, db=db)
        print("Result status:", res.get("status"))
        if "error" in res.get("status", ""):
            print("Error message:", res.get("message"))
        users = res.get("users", [])
        print("Number of users returned:", len(users))
        if users:
            print("First user keys:", list(users[0].keys()))
            if "summary" in users[0]:
                print("Summary:", users[0]["summary"])
    except Exception as e:
        print("Exception:", e)
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test()
