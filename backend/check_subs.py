import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models
from main import get_recursive_subordinates

db = SessionLocal()

users = get_recursive_subordinates(db, "482")
print(f"Found {len(users)} subordinates for 482:")
for u in users:
    print(f"ID: {u.id}, NIK: {u.nik}, Name: {u.full_name}, is_active: {u.is_active}")

