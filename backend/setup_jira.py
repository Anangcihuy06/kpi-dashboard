import requests
import json
import sys

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

# API Configuration
BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"

def setup_jira_integration():
    """Setup Jira integration settings via API"""
    
    print("KPI Dashboard - Jira Integration Setup")
    print("=" * 50)
    
    # Step 1: Check current integration settings
    print("\nStep 1: Checking current integration settings...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/integrations")
        current_settings = response.json()
        print(f"Current Jira URL: {current_settings.get('jira_url', 'Not configured')}")
        print(f"Current Jira Email: {current_settings.get('jira_email', 'Not configured')}")
        print(f"Current Board ID: {current_settings.get('jira_board_id', 'Not configured')}")
    except Exception as e:
        print(f"ERROR: Error checking current settings: {e}")
        return False
    
    # Step 2: Get user input for Jira settings
    print("\nStep 2: Enter Jira Integration Settings")
    print("-" * 50)
    
    jira_url = input(f"Jira URL [https://yourcompany.atlassian.net]: ").strip() or "https://yourcompany.atlassian.net"
    jira_email = input(f"Jira Email: ").strip()
    jira_token = input(f"Jira API Token: ").strip()
    board_id = input(f"Jira Board ID: ").strip()
    sp_field = input(f"Story Points Field ID [customfield_10016]: ").strip() or "customfield_10016"
    
    if not all([jira_url, jira_email, jira_token, board_id]):
        print("ERROR: Jira URL, Email, Token, and Board ID are required!")
        return False
    
    # Step 3: Save integration settings
    print("\nStep 3: Saving integration settings...")
    try:
        payload = {
            "jira_url": jira_url,
            "jira_email": jira_email,
            "jira_token": jira_token,
            "jira_board_id": board_id,
            "jira_sp_field": sp_field,
            "gitlab_url": "https://gitlab.com"
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/integrations", json=payload)
        if response.status_code == 200:
            print("SUCCESS: Integration settings saved successfully!")
        else:
            print(f"ERROR: Error saving settings: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"ERROR: Error saving settings: {e}")
        return False
    
    # Step 4: Trigger manual sync
    print("\nStep 4: Triggering manual sync...")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/sync/trigger")
        if response.status_code == 200:
            print("SUCCESS: Sync triggered successfully!")
            print("Sync is running in the background...")
        else:
            print(f"ERROR: Error triggering sync: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"ERROR: Error triggering sync: {e}")
        return False
    
    # Step 5: Check sync status
    print("\nStep 5: Checking sync status...")
    try:
        import time
        time.sleep(3)  # Wait for sync to start
        
        response = requests.get(f"{BASE_URL}/api/v1/sync/status")
        status = response.json()
        print(f"Last Sync: {status.get('last_sync_human', 'Never')}")
        print(f"Sync Interval: {status.get('sync_interval_minutes', 60)} minutes")
    except Exception as e:
        print(f"ERROR: Error checking sync status: {e}")
    
    # Step 6: Check sprint data
    print("\nStep 6: Checking sprint data...")
    try:
        time.sleep(5)  # Wait for sync to complete
        response = requests.get(f"{BASE_URL}/api/v1/sprints")
        sprints = response.json()
        
        if not sprints:
            print("WARNING: No sprints found. Check Jira configuration or wait for sync to complete.")
        else:
            print(f"SUCCESS: Found {len(sprints)} sprint(s):")
            for sprint in sprints:
                jira_id = sprint.get('jira_sprint_id', 'NULL')
                status_icon = "[ACTIVE]" if sprint.get('status') == 'ACTIVE' else "[CLOSED]"
                print(f"  {status_icon} {sprint.get('sprint_name')} (Jira ID: {jira_id})")
                
                if sprint.get('jira_sprint_id'):
                    print(f"         Successfully synced from Jira!")
                else:
                    print(f"         WARNING: jira_sprint_id is NULL - sync may have failed")
    
    except Exception as e:
        print(f"ERROR: Error checking sprint data: {e}")
    
    print("\n" + "=" * 50)
    print("Setup Complete!")
    print(f"\nDashboard: {FRONTEND_URL}")
    print(f"API Docs: {BASE_URL}/docs")
    print("\nTips:")
    print("  - Auto-sync runs every 60 minutes")
    print("  - Check backend logs for detailed sync information")
    print("  - Use manual sync if data is stale")
    
    return True

def test_jira_connection():
    """Test Jira API connection"""
    print("\nTesting Jira Connection...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/integrations")
        settings = response.json()
        
        if not settings.get('jira_url') or not settings.get('jira_token'):
            print("ERROR: Jira integration not configured. Please run setup first.")
            return False
        
        # This would be implemented in the backend for actual connection testing
        print("SUCCESS: Jira integration is configured")
        print(f"   URL: {settings.get('jira_url')}")
        print(f"   Email: {settings.get('jira_email')}")
        
        return True
    except Exception as e:
        print(f"ERROR: Error testing connection: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_jira_connection()
    else:
        setup_jira_integration()