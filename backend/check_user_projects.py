import sqlite3

conn = sqlite3.connect('c:/Users/ATI-User/KPI-Dashboard/backend/database.db')
c = conn.cursor()

c.execute('''
    SELECT DISTINCT p.id, p.project_name, p.source 
    FROM activities a
    JOIN projects p ON a.project_id = p.id
    WHERE a.user_id = '6518'
''')
print('Projects in activities for Nanang (6518):')
for row in c.fetchall():
    print(row)

c.execute("SELECT id, project_name, external_project_id FROM projects WHERE source='gitlab'")
print('\nAll GitLab projects in DB:')
for row in c.fetchall():
    print(row)

conn.close()
