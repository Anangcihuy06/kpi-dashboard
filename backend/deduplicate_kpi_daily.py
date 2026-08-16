import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal

db = SessionLocal()

print("=== DEDUPLICATING KPIEmployeeDaily RECORDS ===")

# Query all records
all_records = db.query(models.KPIEmployeeDaily).order_by(
    models.KPIEmployeeDaily.user_id,
    models.KPIEmployeeDaily.date,
    models.KPIEmployeeDaily.created_at.desc()
).all()

print(f"Total rows before deduplication: {len(all_records)}")

seen = set()
to_delete = []

for r in all_records:
    # Key is (user_id, date)
    date_key = str(r.date)[:10]
    key = (r.user_id, date_key)
    if key in seen:
        to_delete.append(r)
    else:
        seen.add(key)

print(f"Deleting {len(to_delete)} duplicate rows...")
for r in to_delete:
    db.delete(r)

db.commit()

# Verify remaining rows
rem_count = db.query(models.KPIEmployeeDaily).count()
print(f"Deduplication complete! Remaining distinct rows: {rem_count}")
