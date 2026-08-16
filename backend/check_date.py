import sqlite3
conn = sqlite3.connect('c:/Users/ATI-User/KPI-Dashboard/backend/database.db')
c = conn.cursor()
c.execute("SELECT activity_date, activity_date >= '2026-05-13 00:00:00' FROM activities WHERE activity_date LIKE '2026-05-13%' LIMIT 1")
print("2026-05-13:", c.fetchone())

c.execute("SELECT activity_date, activity_date >= '2026-07-17 00:00:00' FROM activities WHERE activity_date LIKE '2026-07-17%' LIMIT 1")
print("2026-07-17:", c.fetchone())
