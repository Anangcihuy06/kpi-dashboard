import sqlite3
import json

conn = sqlite3.connect('c:/Users/ATI-User/KPI-Dashboard/backend/database.db')
c = conn.cursor()

# Change the Jira rule to use jira_sp (which now stores feature_weight)
variables_jira = json.dumps({"target_sp": 50}) # 50 feature points per sprint
c.execute("UPDATE kpi_rule_metrics SET metric_key='jira_sp', formula_expression='min((jira_sp / target_sp) * 100, 120)', variables=? WHERE metric_key='jira_issues_completed'", (variables_jira,))

conn.commit()
print('Rules updated to use feature weights in jira_sp')
