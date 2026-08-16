import sqlite3

conn = sqlite3.connect('c:/Users/ATI-User/KPI-Dashboard/backend/database.db')
c = conn.cursor()
c.execute("UPDATE kpi_rule_metrics SET formula_expression = 'jira_sp', variables = '{}' WHERE metric_key = 'jira_sp'")
conn.commit()
print('Formula updated')
conn.close()
