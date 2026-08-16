import sqlite3
import json

conn = sqlite3.connect('c:/Users/ATI-User/KPI-Dashboard/backend/database.db')
c = conn.cursor()

# 1. Update jira_sp weight to 0.8 (80%)
c.execute("UPDATE kpi_rule_metrics SET weight = 0.8 WHERE metric_key = 'jira_sp'")

# 2. Delete gitlab_commits metric entirely so it doesn't show in the grading matrix
c.execute("DELETE FROM kpi_rule_metrics WHERE metric_key = 'gitlab_commits'")

conn.commit()
print("Successfully updated kpi_rule_metrics: Removed gitlab_commits, increased jira_sp weight to 0.8")
conn.close()
