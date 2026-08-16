import requests
import json

def test_yearly_details(user_id: str, year: int):
    r = requests.get(f'http://localhost:8000/api/v1/kpi/yearly-performance?user_id={user_id}&year={year}')
    if r.status_code == 200:
        data = r.json().get('data', {})
        print(f"\n=== YEAR {year} DETAILS FOR USER {user_id} ({data.get('full_name')}) ===")
        print("Summary:", json.dumps(data.get('summary'), indent=2))
        print("Details Breakdown:")
        details = data.get('kpi_scores', {}).get('details', [])
        for d in details:
            print(f" - {d.get('metric_key')}: Raw = {d.get('actual_value')}, Formula = {d.get('formula')}, Vars = {d.get('variables')}, Score = {d.get('calculated_score')}, Weighted = {d.get('weighted_score')}")

test_yearly_details('6518', 2025)
test_yearly_details('6518', 2026)
test_yearly_details('9615', 2026)
