import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models

db = SessionLocal()

users = db.query(models.User).filter(models.User.nik == "01.04.19.1905").all()
print(f"Found {len(users)} users for NIK 01.04.19.1905")
for u in users:
    print(f"ID: {u.id}, Name: {u.full_name}, is_active: {u.is_active}, supervisor_id: {u.supervisor_id}")

print("----------")
api_6518 = db.query(models.User).filter(models.User.id == "api_6518").first()
if api_6518:
    print(f"api_6518 exists. NIK: {api_6518.nik}")
else:
    print("api_6518 does not exist")
