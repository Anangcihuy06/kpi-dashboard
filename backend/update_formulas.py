import sqlite3
import json

conn = sqlite3.connect('c:/Users/ATI-User/KPI-Dashboard/backend/database.db')
c = conn.cursor()

# Update Jira formula to use issues_completed
variables_jira = json.dumps({"target_issues": 10})
c.execute("UPDATE kpi_rule_metrics SET metric_key='jira_issues_completed', formula_expression='min((jira_issues_completed / target_issues) * 100, 120)', variables=? WHERE metric_key='jira_sp'", (variables_jira,))

# Update GitLab formula to use commits
variables_gitlab = json.dumps({"target_commits": 30})
c.execute("UPDATE kpi_rule_metrics SET metric_key='gitlab_commits', formula_expression='min((gitlab_commits / target_commits) * 100, 120)', variables=? WHERE metric_key='gitlab_mr'", (variables_gitlab,))

conn.commit()
print('Rules updated')
