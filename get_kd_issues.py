import sqlite3
conn = sqlite3.connect('backend/database.db')
cursor = conn.cursor()
cursor.execute("SELECT issue_key, status, resolved_date FROM raw_jira_issues WHERE issue_key LIKE 'KD-%'")
print(cursor.fetchall())
