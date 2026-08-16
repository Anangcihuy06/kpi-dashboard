import os
import sys
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SeedComprehensive")

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def generate_random_time(start_hour=9, variance_minutes=30):
    dt = datetime(2026, 1, 1, start_hour, 0, 0)
    if variance_minutes < 0:
        variance = random.randint(variance_minutes, 0)
    else:
        variance = random.randint(-variance_minutes, variance_minutes)
    return (dt + timedelta(minutes=variance)).strftime("%H:%M:%S")

def run_seeder():
    db = get_db()
    
    # Check for users
    users = db.query(models.User).all()
    if not users:
        logger.error("No users found. Please run seed.py first to create the organizational structure.")
        return

    logger.info(f"Seeding comprehensive data for {len(users)} users...")

    # Clear old data
    logger.info("Clearing old activities, sprint_kpi_scores, and attendance_records...")
    db.query(models.Activity).delete()
    db.query(models.SprintKPIScore).delete()
    db.query(models.AttendanceRecord).delete()
    db.query(models.KPIEmployeeDaily).delete()
    db.query(models.Sprint).delete()
    db.commit()

    # Create Sprints for YTD 2026 (Jan 1 to Aug 14)
    # 16 sprints (bi-weekly)
    start_date = datetime(2026, 1, 1)
    sprints = []
    for i in range(16):
        end_date = start_date + timedelta(days=13)
        sprint = models.Sprint(
            sprint_name=f"Sprint {i+1} 2026",
            start_date=start_date,
            end_date=end_date,
            status="ACTIVE" if (i == 15) else "CLOSED"
        )
        db.add(sprint)
        sprints.append(sprint)
        start_date = end_date + timedelta(days=1)
    
    db.commit()
    logger.info("Created 16 sprints for 2026.")

    # Get working days in 2026 YTD
    current_date = datetime(2026, 8, 14)
    all_days = [datetime(2026, 1, 1) + timedelta(days=x) for x in range((current_date - datetime(2026, 1, 1)).days + 1)]
    working_days = [d for d in all_days if d.weekday() < 5]

    # Assign performance tiers to users
    top_performers = random.sample(users, min(3, len(users)))
    bottom_performers = random.sample([u for u in users if u not in top_performers], min(2, len(users) - 3))

    for user in users:
        # Determine tier
        if user in top_performers:
            tier = "TOP"
            # Jira SP: 300 - 400
            # GitLab MRs: 90 - 128
            # Attendance: 95% - 100%
        elif user in bottom_performers:
            tier = "BOTTOM"
            # Jira SP: 100 - 180
            # GitLab MRs: 20 - 45
            # Attendance: 70% - 85%
        else:
            tier = "AVERAGE"
            # Jira SP: 190 - 290
            # GitLab MRs: 50 - 80
            # Attendance: 85% - 95%

        logger.info(f"Generating {tier} data for {user.full_name}...")

        # 1. Attendance Records
        if tier == "TOP":
            presence_rate = random.uniform(0.95, 1.0)
            late_rate = random.uniform(0.0, 0.05)
        elif tier == "BOTTOM":
            presence_rate = random.uniform(0.70, 0.85)
            late_rate = random.uniform(0.15, 0.30)
        else:
            presence_rate = random.uniform(0.85, 0.95)
            late_rate = random.uniform(0.05, 0.15)

        for day in working_days:
            # Find matching sprint for the day
            day_sprint = next((s for s in sprints if s.start_date.date() <= day.date() <= s.end_date.date()), sprints[0])
            
            # Determine presence
            if random.random() > presence_rate:
                # Absent
                db.add(models.AttendanceRecord(
                    user_id=user.id,
                    sprint_id=day_sprint.id,
                    date=day.date().isoformat(),
                    status="ABSENT",
                    is_late=False,
                    late_minutes=0
                ))
            else:
                # Present
                is_late = random.random() < late_rate
                if is_late:
                    late_mins = random.randint(5, 60)
                    clock_in = generate_random_time(9, 0)
                    clock_in_dt = datetime.strptime(clock_in, "%H:%M:%S") + timedelta(minutes=late_mins)
                    clock_in_str = clock_in_dt.strftime("%H:%M:%S")
                else:
                    late_mins = 0
                    clock_in_str = generate_random_time(9, -15) # Arrive before 9
                
                db.add(models.AttendanceRecord(
                    user_id=user.id,
                    sprint_id=day_sprint.id,
                    date=day.date().isoformat(),
                    status="LATE" if is_late else "PRESENT",
                    is_late=is_late,
                    late_minutes=late_mins,
                    clock_in=clock_in_str,
                    clock_out=generate_random_time(17, 30)
                ))

        # 2. GitLab Activities (Commits and MRs)
        if tier == "TOP":
            target_mrs = random.randint(90, 128)
            target_commits = random.randint(400, 640)
        elif tier == "BOTTOM":
            target_mrs = random.randint(20, 45)
            target_commits = random.randint(100, 200)
        else:
            target_mrs = random.randint(50, 80)
            target_commits = random.randint(220, 380)

        # Spread MRs across working days
        mr_days = random.sample(working_days, target_mrs)
        for d in mr_days:
            db.add(models.Activity(
                user_id=user.id,
                source="gitlab",
                activity_type="merge_request",
                project_id="P1",
                reference_id=f"MR-{random.randint(1000, 9999)}",
                activity_date=d.date(),
                activity_at=d + timedelta(hours=random.randint(10, 16)),
                activity_metadata={"state": "merged"}
            ))

        commit_days = random.choices(working_days, k=target_commits)
        for d in commit_days:
            db.add(models.Activity(
                user_id=user.id,
                source="gitlab",
                activity_type="commit",
                project_id="P1",
                reference_id=f"commit-{random.randint(10000, 99999)}",
                activity_date=d.date(),
                activity_at=d + timedelta(hours=random.randint(9, 18)),
                activity_metadata={}
            ))

        # 3. Jira Activities (Story Points)
        if tier == "TOP":
            target_sp = random.randint(300, 400)
            target_issues = random.randint(120, 160)
        elif tier == "BOTTOM":
            target_sp = random.randint(100, 180)
            target_issues = random.randint(30, 60)
        else:
            target_sp = random.randint(190, 290)
            target_issues = random.randint(70, 110)

        issue_days = random.sample(working_days, min(target_issues, len(working_days)))
        sp_per_issue = max(1, target_sp // target_issues)
        
        for d in issue_days:
            db.add(models.Activity(
                user_id=user.id,
                source="jira",
                activity_type="issue_completed",
                project_id="J1",
                reference_id=f"JIRA-{random.randint(100, 999)}",
                activity_date=d.date(),
                activity_at=d + timedelta(hours=random.randint(10, 17)),
                activity_metadata={"story_points": sp_per_issue, "status": "Done"}
            ))
            
    db.commit()
    logger.info("Seeding completed successfully!")

if __name__ == "__main__":
    run_seeder()
