import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal

db = SessionLocal()

user = db.query(models.User).filter(models.User.full_name.ilike('%Nanang%')).first()
print(f"Nanang ID: {user.id}")

identities = db.query(models.EmployeeIdentity).filter(models.EmployeeIdentity.user_id == user.id).all()
for idt in identities:
    print(f"Source: {idt.source}, External ID: {idt.external_user_id}")
