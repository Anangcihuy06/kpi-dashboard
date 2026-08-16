import requests, json

r = requests.get('http://localhost:8000/api/v1/kpi/yearly-performance?user_id=6518&year=2025')
print('Status:', r.status_code)
if r.status_code == 200:
    data = r.json().get('data')
    if data:
        print('User:', data.get('full_name'))
        print('Summary 2025:', json.dumps(data.get('summary'), indent=2))
        print('KPI Scores 2025:', json.dumps(data.get('kpi_scores'), indent=2))
    else:
        print('Data is still None!')
