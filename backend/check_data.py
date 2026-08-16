import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal
import models

db = SessionLocal()

nanang = db.query(models.User).filter(models.User.nik == "01.04.19.1905").first()
print(f"Nanang ID: {nanang.id if nanang else 'Not Found'}")

if nanang:
    attendance = db.query(models.AttendanceRecord).filter(models.AttendanceRecord.user_id == nanang.id).count()
    activities = db.query(models.Activity).filter(models.Activity.user_id == nanang.id).count()
    daily_kpis = db.query(models.KPIEmployeeDaily).filter(models.KPIEmployeeDaily.user_id == nanang.id).count()
    print(f"Attendance Records: {attendance}")
    print(f"Activities: {activities}")
    print(f"Daily KPIs: {daily_kpis}")
    
    jira_ident = db.query(models.EmployeeIdentity).filter(models.EmployeeIdentity.user_id == nanang.id, models.EmployeeIdentity.source == 'jira').first()
    if jira_ident:
        print(f"Jira Identity: {jira_ident.external_user_id}")
    else:
        print("No Jira Identity")
        
    gitlab_ident = db.query(models.EmployeeIdentity).filter(models.EmployeeIdentity.user_id == nanang.id, models.EmployeeIdentity.source == 'gitlab').first()
    if gitlab_ident:
        print(f"GitLab Identity: {gitlab_ident.external_user_id}")
    else:
        print("No GitLab Identity")
