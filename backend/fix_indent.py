import sys

with open("c:/Users/ATI-User/KPI-Dashboard/backend/comprehensive_sync.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
in_block = False
for i, line in enumerate(lines):
    if i >= 745 and i <= 859: # 746 to 860 in 1-based indexing
        # Add 4 spaces of indentation
        if line.strip():
            new_lines.append("    " + line)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open("c:/Users/ATI-User/KPI-Dashboard/backend/comprehensive_sync.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
