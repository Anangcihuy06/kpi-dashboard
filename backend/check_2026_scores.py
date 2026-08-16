import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Get sprints in 2026
cursor.execute("SELECT id, name FROM sprints WHERE start_date >= '2026-01-01'")
sprints = cursor.fetchall()
sprint_ids = [s[0] for s in sprints]
sprint_names = {s[0]: s[1] for s in sprints}

print("=== 2026 KPI Scores ===")
for sid in sprint_ids:
    print(f"\nSprint: {sprint_names[sid]}")
    cursor.execute("SELECT users.full_name, sprint_kpi_scores.final_score FROM sprint_kpi_scores JOIN users ON sprint_kpi_scores.user_id = users.id WHERE sprint_id = ?", (sid,))
    scores = cursor.fetchall()
    for row in scores:
        print(f"  {row[0]}: {row[1]}")

conn.close()
