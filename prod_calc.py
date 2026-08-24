import requests, time, sys

print('Triggering Sync Data on PROD...')
try:
    res = requests.post('https://services-kpi-production.up.railway.app/api/v1/sync/data', timeout=10)
    job_id = res.json().get('job_id')
    print('Sync Job:', job_id)
    if job_id:
        while True:
            st = requests.get(f'https://services-kpi-production.up.railway.app/api/v1/jobs/{job_id}').json()
            if st.get('status') in ['COMPLETED', 'FAILED']:
                print('Sync finished:', st.get('status'))
                break
            time.sleep(3)
except Exception as e:
    print('Sync Error:', e)

print('\nTriggering KPI Calc on PROD...')
try:
    res = requests.post('https://services-kpi-production.up.railway.app/api/v1/kpi/calculate/2026?force=true', timeout=10)
    job_id = res.json().get('job_id')
    print('Calc Job:', job_id)
    if job_id:
        while True:
            st = requests.get(f'https://services-kpi-production.up.railway.app/api/v1/jobs/{job_id}').json()
            if st.get('status') in ['COMPLETED', 'FAILED']:
                print('Calc finished:', st.get('status'))
                break
            time.sleep(3)
except Exception as e:
    print('Calc Error:', e)

print('\nFetching scores for ALL users...')
try:
    # No /admin/users endpoint. Let's just fetch for Yanes Arfian (1276) since we know the ID from local DB.
    # And Anang Cihuy / Ansha / whoever is testing. I will fetch for a few known IDs.
    known_ids = ["1276", "8515", "482", "7690", "9615", "7724", "6856", "6592", "7052", "6518", "6182"]
    for uid in known_ids:
        res = requests.get(f"https://services-kpi-production.up.railway.app/api/v1/kpi/yearly-performance?year=2026&user_id={uid}", timeout=10)
        if res.status_code == 200:
            data = res.json()
            if 'data' in data:
                u_name = data['data']['user']['full_name']
                print(f"{u_name} (ID: {uid}): Overall={data['data']['summary']['overall_score']}, Issues={data['data']['summary']['total_issues_completed']}, Points={data['data']['summary']['total_story_points_completed']}")
except Exception as e:
    print('Fetch Error:', e)
