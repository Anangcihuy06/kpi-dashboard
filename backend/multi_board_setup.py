"""
Multi-Project Setup Script
Helps configure users with their specific Jira board assignments
"""

import requests
from database import SessionLocal
from models import User, IntegrationSetting, JiraBoard
from encrypt import encrypt_val

def setup_multi_project_environment():
    print("=== KPI Dashboard Multi-Project Environment Setup ===\n")
    
    db = SessionLocal()
    settings = db.query(IntegrationSetting).first()
    
    if not settings:
        print("Integration settings not found. Please configure Jira settings first.")
        return
    
    # Get all available boards from Jira
    token = settings.jira_token_encrypted
    if token:
        from encrypt import decrypt_val
        token = decrypt_val(token)
    
    jira_auth = (settings.jira_email, token)
    boards_url = f'{settings.jira_url}/rest/agile/1.0/board'
    
    print("Fetching all available Jira boards...\n")
    
    try:
        response = requests.get(boards_url, auth=jira_auth, timeout=10)
        if response.status_code == 200:
            all_boards = response.json().get('values', [])
            print(f"Found {len(all_boards)} total boards\n")
            
            # Display boards with index for easy selection
            for i, board in enumerate(all_boards, 1):
                print(f"{i}. {board.get('name')} (ID: {board.get('id')}, Type: {board.get('type')})")
                print(f"   Project: {board.get('location', {}).get('name', 'Unknown')}\n")
            
            # Get default boards to sync
            print("\n=== Configure Default Boards for System ===")
            default_boards = input("Enter board IDs to sync by default (comma-separated): ").strip()
            
            if default_boards:
                board_list = [bid.strip() for bid in default_boards.split(',')]
                settings.jira_board_ids = board_list
                
                # Set the first one as default
                if board_list:
                    settings.default_jira_board_id = board_list[0]
                
                db.commit()
                print(f"\n✅ Configured {len(board_list)} default boards: {board_list}")
                print(f"✅ Default board ID: {board_list[0]}")
            
            # Configure user assignments
            print("\n=== Configure User-Board Assignments ===")
            users = db.query(User).filter(User.is_active == True).all()
            
            print(f"Found {len(users)} active users\n")
            
            for user in users:
                print(f"\nUser: {user.full_name} (ID: {user.id})")
                print(f"Current board assignments: {user.jira_board_ids or 'None'}")
                print(f"Current active board: {user.current_active_board or 'None'}")
                
                choice = input(f"Configure board assignments for {user.full_name}? (y/n): ").lower().strip()
                
                if choice == 'y':
                    user_boards = input("Enter board IDs (comma-separated): ").strip()
                    if user_boards:
                        user_board_list = [bid.strip() for bid in user_boards.split(',')]
                        user.jira_board_ids = user_board_list
                        
                        # Set current active board
                        if user_board_list:
                            active_choice = input(f"Set current active board (choose from {user_board_list}): ").strip()
                            if active_choice:
                                user.current_active_board = active_choice
                            else:
                                user.current_active_board = user_board_list[0]
                        
                        db.commit()
                        print(f"✅ Configured board assignments for {user.full_name}")
        
        else:
            print(f"Error fetching boards: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    
    print("\n=== Setup Summary ===")
    
    # Get updated settings
    db.refresh(settings)
    print(f"Default system boards: {settings.jira_board_ids or 'None'}")
    print(f"Default active board: {settings.default_jira_board_id or 'None'}")
    
    # Count configured users
    configured_users = db.query(User).filter(
        User.jira_board_ids != None,
        User.jira_board_ids != '[]',
        User.is_active == True
    ).count()
    
    print(f"Users with board assignments: {configured_users}/{len(users)}")
    
    db.close()
    print("\n=== Multi-Project Setup Complete ===")

def sync_all_configured_boards():
    """Manually trigger sync for all configured boards"""
    print("=== Syncing All Configured Boards ===\n")
    
    db = SessionLocal()
    settings = db.query(IntegrationSetting).first()
    
    if settings:
        from multi_board_sync import sync_all_boards_sprints
        
        results = sync_all_boards_sprints(db, settings)
        
        print("\n=== Sync Results ===")
        for board_id, result in results.items():
            print(f"Board {board_id}:")
            print(f"  Active sprints: {result.get('active', 0)}")
            print(f"  Closed sprints: {result.get('closed', 0)}")
            if result.get('errors'):
                print(f"  Errors: {len(result['errors'])}")
                for error in result['errors']:
                    print(f"    - {error}")
    
    db.close()
    print("\n=== Board Sync Complete ===")

def test_user_sprint_discovery():
    """Test sprint discovery for each user"""
    print("=== Testing User Sprint Discovery ===\n")
    
    db = SessionLocal()
    settings = db.query(IntegrationSetting).first()
    
    if settings:
        from multi_board_sync import get_user_active_sprint
        
        users = db.query(User).filter(User.is_active == True).all()
        
        for user in users:
            user_sprint = get_user_active_sprint(db, user, settings)
            
            print(f"User: {user.full_name} (ID: {user.id})")
            print(f"  Assigned boards: {user.jira_board_ids or 'None'}")
            print(f"  Current active board: {user.current_active_board or 'None'}")
            
            if user_sprint:
                print(f"  Active sprint: {user_sprint.sprint_name} (Jira ID: {user_sprint.jira_sprint_id})")
                print(f"  Sprint board: {user_sprint.jira_board_id}")
            else:
                print(f"  No active sprint found")
            
            print()
    
    db.close()
    print("=== Sprint Discovery Test Complete ===")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'setup':
            setup_multi_project_environment()
        elif command == 'sync':
            sync_all_configured_boards()
        elif command == 'test':
            test_user_sprint_discovery()
        else:
            print("Unknown command. Available commands: setup, sync, test")
    else:
        print("Multi-Project Management Tool")
        print("Usage: python multi_board_setup.py [command]")
        print("Commands:")
        print("  setup  - Configure user-board assignments")
        print("  sync   - Sync all configured boards")
        print("  test   - Test user sprint discovery")