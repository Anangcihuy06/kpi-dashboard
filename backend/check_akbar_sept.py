import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Get Akbar
cursor.execute("SELECT id FROM users WHERE full_name LIKE '%Akbar%'")
akbar_id = cursor.fetchone()[0]

cursor.execute('SELECT date, attendance_days, late_count, late_percentage FROM kpi_employee_daily WHERE user_id = ? AND date LIKE "2025-09%" ORDER BY date', (akbar_id,))
for row in cursor.fetchall():
    print(f"Date: {row[0]} | Attendance: {row[1]} | Late: {row[2]} ({row[3]}%)")

conn.close()
