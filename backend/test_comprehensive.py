"""
Test the new comprehensive KPI system following the documentation architecture
"""

import requests
from datetime import datetime, timedelta
from database import SessionLocal
import models

BASE_URL = "http://localhost:8000"

def test_database_schema():
    """Test that all new tables are created"""
    print("=== Testing Database Schema ===\n")
    
    db = SessionLocal()
    
    # Test new tables exist
    tables_to_test = [
        ("Employee Identity", models.EmployeeIdentity),
        ("Sync State", models.SyncState),
        ("Sync Logs", models.SyncLog),
        ("Projects", models.Project),
        ("Activities", models.Activity),
        ("Daily KPI", models.KPIEmployeeDaily),
        ("Raw GitLab Commits", models.RawGitLabCommit),
        ("Raw Jira Worklogs", models.RawJiraWorklog),
        ("Issue Sprint History", models.IssueSprintHistory),
        ("Sprint History", models.SprintHistory)
    ]
    
    for table_name, model_class in tables_to_test:
        try:
            record_count = db.query(model_class).count()
            print(f"✓ {table_name}: {record_count} records")
        except Exception as e:
            print(f"✗ {table_name}: ERROR - {str(e)}")
    
    db.close()
    print()

def test_time_range_kpi():
    """Test time-range based KPI endpoint"""
    print("=== Testing Time-Range KPI ===\n")
    
    # Test with a recent week
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    
    request_data = {
        "from_date": week_ago.strftime("%Y-%m-%d"),
        "to_date": today.strftime("%Y-%m-%d"),
        "user_ids": []  # Current user only
    }
    
    try:
        # Login first to get token
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "username": "01.05.13.500",
            "password": "abcd1234"
        }, timeout=10)
        
        if login_response.status_code != 200:
            print("✗ Login failed, cannot test time-range KPI")
            return
        
        user_data = login_response.json()
        token = user_data.get("token")
        user_id = user_data.get("user", {}).get("id")
        
        print(f"Testing time-range KPI for user: {user_id}")
        print(f"Date range: {request_data['from_date']} to {request_data['to_date']}")
        print()
        
        kpi_response = requests.post(
            f"{BASE_URL}/api/v1/kpi/time-range",
            params={"user_id": user_id},
            json=request_data,
            timeout=15
        )
        
        if kpi_response.status_code == 200:
            result = kpi_response.json()
            print("✓ Time-range KPI endpoint working!")
            print()
            
            # Display results
            print(f"Period: {result['period']['from_date']} to {result['period']['to_date']}")
            print(f"Total Users: {result['total_users']}")
            print()
            
            for user_result in result.get("users", []):
                print(f"User: {user_result['full_name']}")
                print(f"  - Projects: {user_result['summary']['projects_count']}")
                print(f"  - Sprints: {user_result['summary']['sprints_count']}")
                print(f"  - Total Activities: {user_result['summary']['total_activities']}")
                print(f"  - Commits: {user_result['summary']['total_commits']}")
                print(f"  - MRs Merged: {user_result['summary']['total_mrs_merged']}")
                print(f"  - Worklog Hours: {user_result['summary']['total_worklog_hours']}")
                print(f"  - Issues Completed: {user_result['summary']['total_issues_completed']}")
                print(f"  - KPI Scores:")
                print(f"    - Overall: {user_result['kpi_scores']['overall']}")
                print(f"    - Delivery: {user_result['kpi_scores']['delivery']}")
                print(f"    - Engineering: {user_result['kpi_scores']['engineering']}")
                print(f"    - Effort: {user_result['kpi_scores']['effort']}")
                print()
        else:
            print(f"✗ Time-range KPI failed: {kpi_response.status_code}")
            print(kpi_response.text)
            
    except Exception as e:
        print(f"✗ Error testing time-range KPI: {str(e)}")

def test_user_identities():
    """Test user identity mapping"""
    print("=== Testing User Identity Mapping ===\n")
    
    try:
        # Login first
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "username": "01.05.13.500",
            "password": "abcd1234"
        }, timeout=10)
        
        if login_response.status_code != 200:
            print("✗ Login failed, cannot test identities")
            return
        
        user_data = login_response.json()
        user_id = user_data.get("user", {}).get("id")
        
        print(f"Testing identity mapping for user: {user_id}")
        print()
        
        identity_response = requests.get(
            f"{BASE_URL}/api/v1/users/{user_id}/identities",
            timeout=10
        )
        
        if identity_response.status_code == 200:
            result = identity_response.json()
            print(f"✓ Identity endpoint working!")
            print()
            
            print(f"User: {result['full_name']} ({result['user_id']})")
            print(f"Identities Found: {len(result['identities'])}")
            print()
            
            for identity in result.get("identities", []):
                print(f"  {identity['source'].upper()}:")
                print(f"    - External ID: {identity['external_user_id']}")
                print(f"    - Username: {identity['username']}")
                print(f"    - Email: {identity['email']}")
                print(f"    - Verified: {identity['is_verified']}")
                print()
        else:
            print(f"✗ Identity endpoint failed: {identity_response.status_code}")
            print(identity_response.text)
            
    except Exception as e:
        print(f"✗ Error testing identities: {str(e)}")

def test_user_activities():
    """Test user activity timeline"""
    print("=== Testing Activity Timeline ===\n")
    
    try:
        # Login first
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "username": "01.05.13.500",
            "password": "abcd1234"
        }, timeout=10)
        
        if login_response.status_code != 200:
            print("✗ Login failed, cannot test activities")
            return
        
        user_data = login_response.json()
        token = user_data.get("token")
        user_id = user_data.get("user", {}).get("id")
        
        # Test with recent week
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        
        from_date = week_ago.strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")
        
        print(f"Testing activity timeline for user: {user_id}")
        print(f"Date range: {from_date} to {to_date}")
        print()
        
        activity_response = requests.get(
            f"{BASE_URL}/api/v1/kpi/activities",
            params={
                "user_id": user_id,
                "from_date": from_date,
                "to_date": to_date
            },
            timeout=10
        )
        
        if activity_response.status_code == 200:
            result = activity_response.json()
            print("✓ Activity endpoint working!")
            print()
            
            print(f"User: {result['full_name']} ({result['user_id']})")
            print(f"Time Range: {result['time_range']['from_date']} to {result['time_range']['to_date']}")
            print(f"Total Activities: {result['total_activities']}")
            print()
            
            print("Recent Activities:")
            for activity in result.get("activities", [])[:10]:  # Show first 10
                print(f"  - {activity['activity_type']} ({activity['source']})")
                print(f"    Date: {activity['activity_date']}")
                print(f"    Ref ID: {activity['reference_id']}")
                
                if activity.get("project"):
                    print(f"    Project: {activity['project']['name']}")
                
                if activity.get("sprint"):
                    print(f"    Sprint: {activity['sprint']['sprint_name']}")
                
                print()
        else:
            print(f"✗ Activity endpoint failed: {activity_response.status_code}")
            print(activity_response.text)
            
    except Exception as e:
        print(f"✗ Error testing activities: {str(e)}")

def demonstrate_architecture_flow():
    """Demonstrate the new architecture flow from documentation"""
    print("=== Architecture Flow Demonstration ===\n")
    
    print("According to documentation, the new flow is:")
    print()
    print("1. TIME RANGE")
    print("   ↓")
    print("2. COLLECT ALL ACTIVITIES (GitLab + Jira)")
    print("   ↓")
    print("3. NORMALIZE (Standardized activity model)")
    print("   ↓")
    print("4. MAP EMPLOYEE (Identity mapping)")
    print("   ↓")
    print("5. MAP PROJECT (Multi-project support)")
    print("   ↓")
    print("6. MAP SPRINT (Historical tracking)")
    print("   ↓")
    print("7. CALCULATE KPI (Daily aggregated)")
    print("   ↓")
    print("8. AGGREGATE (Time range summaries)")
    print("   ↓")
    print("9. DASHBOARD (Time-range queries)")
    print()
    
    print("Key Improvements:")
    print("- ✓ Multi-project employee support")
    print("- ✓ Time-range based KPI (not just sprint-based)")
    print("- ✓ Raw data storage for audit and reprocessing")
    print("- ✓ Identity mapping system (HRIS ↔ GitLab ↔ Jira)")
    print("- ✓ Activity normalization layer")
    print("- ✓ Incremental sync with state tracking")
    print("- ✓ Daily KPI aggregation for performance")
    print("- ✓ Historical state tracking (sprint/issue history)")
    print()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "schema":
            test_database_schema()
        elif command == "kpi":
            test_time_range_kpi()
        elif command == "identities":
            test_user_identities()
        elif command == "activities":
            test_user_activities()
        elif command == "flow":
            demonstrate_architecture_flow()
        elif command == "all":
            test_database_schema()
            test_user_identities()
            test_time_range_kpi()
            test_user_activities()
        else:
            print("Unknown command. Available commands: schema, kpi, identities, activities, flow, all")
    else:
        print("Comprehensive KPI System Test")
        print("Usage: python test_comprehensive.py [command]")
        print("Commands:")
        print("  schema     - Test database schema")
        print("  kpi        - Test time-range KPI")
        print("  identities  - Test user identity mapping")
        print("  activities  - Test activity timeline")
        print("  flow       - Show architecture flow")
        print("  all        - Run all tests")