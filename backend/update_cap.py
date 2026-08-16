import sqlite3

conn = sqlite3.connect('c:/Users/ATI-User/KPI-Dashboard/backend/database.db')
c = conn.cursor()
c.execute("UPDATE kpi_rule_metrics SET cap_score = 9999.0 WHERE metric_key = 'jira_sp'")
conn.commit()
print('Cap score updated')
conn.close()
