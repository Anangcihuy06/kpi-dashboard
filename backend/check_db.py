import sqlite3

conn = sqlite3.connect('kpi_dashboard.db')
cursor = conn.cursor()

# Find Nanang Wahyudi
cursor.execute("SELECT id, full_name, jira_account_id, gitlab_username FROM users WHERE full_name LIKE '%Nanang%'")
user = cursor.fetchone()
if not user:
    print('User not found')
else:
    user_id = user[0]
    print(f'User: {user}')
    
    # Get activities
    cursor.execute('SELECT source, activity_type, count(*) FROM activities WHERE user_id=? GROUP BY source, activity_type', (user_id,))
    rows = cursor.fetchall()
    print('Activities:', rows)
    
    # Check identity
    cursor.execute('SELECT platform, external_user_id, external_username FROM employee_identities WHERE user_id=?', (user_id,))
    identities = cursor.fetchall()
    print('Identities:', identities)
