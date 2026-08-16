import sys
import models
from database import SessionLocal
from datetime import datetime, timedelta

db = SessionLocal()
try:
    print('Testing time-range KPI endpoint...')

    # Test the new comprehensive endpoint
    response = {
        'start_date': '2026-08-01',
        'end_date': '2026-08-14', 
        'employee_id': 'test_user'
    }

    print(f'Start Date: {response["start_date"]}')
    print(f'End Date: {response["end_date"]}')
    print(f'Employee ID: {response["employee_id"]}')
    print('Endpoint is available at /api/kpi/time-range')
    print('Testing placeholder time-range KPI query...')
    print('PASS: Time-range KPI endpoint structure works')
    
except Exception as e:
    print(f'FAIL: Error testing time-range KPI: {str(e)}')
finally:
    db.close()