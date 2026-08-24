import os
from sqlalchemy import text
from backend.database import SessionLocal
from backend.models import KPIRule, KPIRuleMetric, Division, User

db = SessionLocal()

print("KPIRULES:")
rules = db.query(KPIRule).all()
for r in rules:
    print(r.id, r.name, r.division_id, r.group_id)

print("\nDIVISIONS:")
divs = db.query(Division).all()
for d in divs:
    print(d.id, d.code, d.name)

print("\nUSERS:")
users = db.query(User).all()
for u in users:
    print(u.id, u.nik, u.full_name, u.division_id, u.group_id)
