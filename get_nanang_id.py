import sqlite3
conn = sqlite3.connect('backend/database.db')
cursor = conn.cursor()
cursor.execute("SELECT id, full_name FROM users WHERE full_name LIKE '%Nanang%'")
print(cursor.fetchall())
