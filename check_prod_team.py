import json
try:
    with open('nanang_team.json') as f:
        data = json.load(f)
    if 'data' not in data:
        print(f"Data not found, keys: {data.keys()}")
    for user in data.get('data', []):
        if user.get('nik') in ['9030019', '201601004', '202302008']: # Nanang and Ansha
            print(f"{user['full_name']} (NIK: {user['nik']})")
            for detail in user.get('kpi_scores', {}).get('details', []):
                if 'complexity' in detail['metric_key'].lower():
                    print(f"  {detail['metric_key']}: Raw={detail['raw_score']}, Capped={detail['capped_score']}, Weighted={detail['weighted_score']}")
                    print(f"    Formula used: {detail['formula_used']}")
                    print(f"    Variables: {detail['input_variables']}")
except Exception as e:
    print(f"Error: {e}")
