import sqlite3
import os
import sys

db_path = 'database.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("""
SELECT users.full_name, date, COUNT(*) as c
FROM kpi_employee_daily 
JOIN users ON kpi_employee_daily.user_id = users.id 
GROUP BY user_id, date 
HAVING c > 1 
LIMIT 10
""")
rows = c.fetchall()
for row in rows:
    print(row)

c.execute("SELECT COUNT(*) FROM kpi_employee_daily")
print("Total rows:", c.fetchone()[0])
