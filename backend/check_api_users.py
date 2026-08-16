import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models

db = SessionLocal()

users = db.query(models.User).filter(models.User.id.like("api_%")).all()
print(f"Found {len(users)} users with 'api_' prefix:")
for u in users:
    print(f"ID: {u.id}, NIK: {u.nik}, Name: {u.full_name}, is_active: {u.is_active}, supervisor_id: {u.supervisor_id}")
