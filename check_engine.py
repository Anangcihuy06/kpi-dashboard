import sys
sys.path.insert(0, './backend')
from database import SessionLocal
import models
from yearly_kpi_engine import YearlyKPIEngine
from datetime import datetime

def test():
    db = SessionLocal()
    try:
        user_id = "482"
        aggregated_metrics = {
            "gitlab_commits": 0, "gitlab_mr": 0, "gitlab_mr_merged": 0, "jira_sp": 0,
            "raw_jira_sp": 0, "complexity_sp": 0, "jira_issues_completed": 0,
            "worklog_hours": 0, "attendance_days": 0, "attendance": 0, "late_count": 0,
            "late_percentage": 0, "founder_sp_credit": 0,
            "max_raw_sp": 1, "max_complexity_sp": 1, "max_issues_cnt": 1, "max_founder_sp": 1
        }
        res = YearlyKPIEngine.calculate_yearly_kpi(db, user_id, datetime(2026, 1, 1), datetime(2026, 12, 31), aggregated_metrics, 1)
        print("Engine Result Keys:", res.keys())
        print("Engine Result Error:", res.get("error"))
    finally:
        db.close()

if __name__ == "__main__":
    test()
