import sqlite3

conn = sqlite3.connect('c:/Users/ATI-User/KPI-Dashboard/backend/database.db')
c = conn.cursor()

# Find max story points across ALL users in 2026
c.execute("""
    SELECT user_id, SUM(story_points_completed) as total_sp
    FROM kpi_employee_daily
    WHERE date >= '2026-01-01' AND date <= '2026-12-31'
    GROUP BY user_id
    ORDER BY total_sp DESC
""")
print("Story Points per User across the entire system:")
users_sp = c.fetchall()
for u in users_sp:
    print(u)

conn.close()
