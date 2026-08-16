import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute('SELECT id, nik, full_name FROM users')
users = {row[0]: {'nik': row[1], 'name': row[2]} for row in cursor.fetchall()}

cursor.execute('SELECT user_id, date, attendance_days, late_count, late_percentage, normal_percentage FROM kpi_employee_daily')
for row in cursor.fetchall():
    user = users.get(row[0], {'name': 'Unknown'})
    print(f"User: {user['name']} | Date: {row[1]} | Attendance: {row[2]} | Late: {row[3]} ({row[4]}%)")

conn.close()
