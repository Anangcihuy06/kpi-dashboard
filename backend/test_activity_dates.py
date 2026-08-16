import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
from datetime import datetime
import models
from database import SessionLocal

db = SessionLocal()

user = db.query(models.User).filter(models.User.full_name.ilike('%Nanang%')).first()

activities = db.query(models.Activity).filter(
    models.Activity.user_id == user.id,
    models.Activity.source == "jira"
).all()

act_2026 = [a for a in activities if a.activity_date.year == 2026]
act_2025 = [a for a in activities if a.activity_date.year == 2025]
act_other = [a for a in activities if a.activity_date.year not in [2025, 2026]]

print(f"Total Jira activities: {len(activities)}")
print(f"2026 activities: {len(act_2026)}")
print(f"2025 activities: {len(act_2025)}")
print(f"Other activities: {len(act_other)}")
