import sqlite3

conn = sqlite3.connect('c:/Users/ATI-User/KPI-Dashboard/backend/database.db')
c = conn.cursor()

c.execute("SELECT * FROM employee_identity WHERE user_id = '6518'")
print("Identities for Nanang (6518):")
for row in c.fetchall():
    print(row)

c.execute("SELECT DISTINCT author_email, author_name FROM raw_gitlab_commits WHERE author_email LIKE '%nanang%' OR author_name LIKE '%nanang%'")
print("\nRaw GitLab commits matching 'nanang':")
for row in c.fetchall():
    print(row)

c.execute("""
    SELECT p.project_name, count(c.id) 
    FROM raw_gitlab_commits c 
    JOIN projects p ON c.project_id = p.id 
    WHERE c.author_email LIKE '%nanang%' OR c.author_name LIKE '%nanang%'
    GROUP BY p.project_name
""")
print("\nProjects with raw commits matching 'nanang':")
for row in c.fetchall():
    print(row)

conn.close()
