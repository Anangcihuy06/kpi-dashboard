import os
import sqlite3

db_path = 'c:/Users/ATI-User/KPI-Dashboard/backend/database.db'
if not os.path.exists(db_path):
    print("DB not found")
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Get users
c.execute("SELECT id, full_name FROM users WHERE full_name LIKE 'Adian%'")
user = c.fetchone()
if not user:
    print("User not found")
    exit()

user_id = user[0]
print(f"User: {user[1]} ({user_id})")

# Test original logic
c.execute("""
SELECT SUM(attendance_days) 
FROM kpi_employee_daily 
WHERE user_id = ? AND strftime('%Y', date) = '2026'
""", (user_id,))
original_sum = c.fetchone()[0]
print(f"Original logic sum: {original_sum}")

# Test new deduplicated logic
c.execute("""
SELECT SUM(attendance_days) FROM (
    SELECT date, MAX(attendance_days) as attendance_days
    FROM kpi_employee_daily
    WHERE user_id = ? AND strftime('%Y', date) = '2026'
    GROUP BY date
)
""", (user_id,))
new_sum = c.fetchone()[0]
print(f"New logic sum: {new_sum}")

