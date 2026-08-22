import sqlite3
conn = sqlite3.connect('backend/database.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM employee_identity WHERE user_id = '6518'")
print(cursor.fetchall())
