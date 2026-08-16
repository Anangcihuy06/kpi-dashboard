with open('comprehensive_sync.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "logger.info(f\"Synced {issues_synced} new Jira issues ({len(issues)} processed) for {user.full_name}\")" in line:
        lines[i+1] = ""
        lines[i+2] = "            start_at += max_results\n"
        lines[i+3] = "            if start_at >= data.get('total', 0):\n"
        lines[i+4] = "                break\n"
        lines[i+5] = "        else:\n"
        lines[i+6] = "            logger.error(f\"Failed to fetch Jira issues for {user.full_name}: {response.status_code} {response.text}\")\n"
        lines[i+7] = "            break\n"

with open('comprehensive_sync.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
