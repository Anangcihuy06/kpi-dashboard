import sys
sys.path.insert(0, 'c:/Users/ATI-User/KPI-Dashboard/backend')
import models
from database import SessionLocal

db = SessionLocal()

users = db.query(models.User).filter(models.User.is_active == True).all()

print("=== ALL ACTIVE USERS & IDENTITIES ===")
for u in users:
    j_ident = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == u.id,
        models.EmployeeIdentity.source == 'jira'
    ).first()
    
    gl_idents = db.query(models.EmployeeIdentity).filter(
        models.EmployeeIdentity.user_id == u.id,
        models.EmployeeIdentity.source == 'gitlab'
    ).all()
    
    print(f"User ID: {u.id:<5} | Name: {u.full_name:<30} | Roles: {u.roles} | Email: {u.email}")
    print(f"   - Jira Account ID: {j_ident.external_user_id if j_ident else 'None'}")
    print(f"   - GitLab Emails: {[i.email for i in gl_idents] if gl_idents else 'None'}")
