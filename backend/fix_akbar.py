import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Find Akbar
cursor.execute("SELECT id, full_name, email FROM users WHERE full_name LIKE '%Akbar%'")
akbar = cursor.fetchone()
print(f"Akbar: {akbar}")

conn.close()
