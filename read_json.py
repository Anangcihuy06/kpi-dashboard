import json

try:
    with open('nanang_team.json') as f:
        data = json.load(f)

    for member in data.get('members', []):
        name = member['user_name']
        if 'nanang' in name.lower() or 'ansha' in name.lower():
            print(f'\n=== {name} ===')
            print(f"Total Score: {member.get('final_kpi_score')}")
            for m in member.get('metrics_breakdown', []):
                print(f"  {m.get('metric_name')}: raw={m.get('raw_score')} capped={m.get('capped_score')} weight={m.get('weight')}% weighted={m.get('weighted_score')}")
except Exception as e:
    print(e)
