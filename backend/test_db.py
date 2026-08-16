import sqlite3
conn = sqlite3.connect('c:/Users/ATI-User/KPI-Dashboard/backend/database.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM activities WHERE user_id='6518' AND activity_type='commit'")
print(f'Nanang commits in activities: {c.fetchone()[0]}')
c.execute("SELECT COUNT(*) FROM raw_gitlab_commits WHERE author_name LIKE '%nanang%' OR author_name LIKE '%anang%'")
print(f'Nanang commits in raw_gitlab_commits: {c.fetchone()[0]}')
