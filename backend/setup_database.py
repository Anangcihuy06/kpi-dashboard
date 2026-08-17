#!/usr/bin/env python3
"""
Production Database Setup Script
This script helps set up the database for production deployment
"""

import os
import sys
from database import engine, Base, SessionLocal
from models import Division, User, IntegrationSetting
from sqlalchemy import text

def setup_database():
    """Set up the database with required initial data"""
    print("Setting up KPI Dashboard database...")
    
    try:
        # Create all tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully")
        
        # Check if divisions exist
        db = SessionLocal()
        try:
            existing_divisions = db.query(Division).count()
            print(f"Existing divisions: {existing_divisions}")
            
            if existing_divisions == 0:
                print("Creating default divisions...")
                divisions = [
                    Division(code="IT", name="IT & Engineering", description="Information Technology Division"),
                    Division(code="HR", name="Human Resources", description="Human Resources Division"),
                    Division(code="FINANCE", name="Finance", description="Finance Division"),
                    Division(code="SALES", name="Sales", description="Sales Division"),
                    Division(code="MARKETING", name="Marketing", description="Marketing Division")
                ]
                
                for div in divisions:
                    db.add(div)
                
                db.commit()
                print(f"Created {len(divisions)} default divisions")
            else:
                print("Divisions already exist")
                
            # Check if integration settings exist
            existing_settings = db.query(IntegrationSetting).count()
            if existing_settings == 0:
                print("Creating default integration settings...")
                default_settings = IntegrationSetting(
                    jira_url="",
                    jira_email="", 
                    jira_token_encrypted="",
                    jira_board_ids=[],
                    default_jira_board_id="",
                    jira_sp_field="customfield_10016",
                    gitlab_url="https://gitlab.com",
                    gitlab_token_encrypted=""
                )
                db.add(default_settings)
                db.commit()
                print("Default integration settings created")
            else:
                print("Integration settings already exist")
                
        except Exception as e:
            db.rollback()
            print(f"Error during data setup: {e}")
            raise
        finally:
            db.close()
            
        # Verify database connection and basic queries
        print("\nVerifying database setup...")
        with engine.connect() as conn:
            # Test basic query
            result = conn.execute(text('SELECT 1'))
            assert result.scalar() == 1, "Basic query failed"
            print("Basic query test passed")
            
            # Verify tables exist
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            required_tables = ['users', 'divisions', 'sprints', 'kpi_rules', 'integration_settings']
            
            for table in required_tables:
                if table in tables:
                    print(f"Table '{table}' exists")
                else:
                    print(f"Table '{table}' missing!")
                    return False
                    
        print("\nDatabase setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"\nDatabase setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def diagnose_database():
    """Diagnose potential database issues"""
    print("\nDiagnosing database health...")
    
    try:
        # Check environment variables
        db_url = os.environ.get("DATABASE_URL", "sqlite:///./database.db")
        print(f"DATABASE_URL: {'***' if 'postgresql' in db_url or 'mysql' in db_url else db_url}")
        
        # Test basic connection
        with engine.connect() as conn:
            result = conn.execute(text('SELECT COUNT(*) FROM divisions'))
            div_count = result.scalar()
            print(f"Divisions count: {div_count}")
            
            result = conn.execute(text('SELECT COUNT(*) FROM users'))  
            user_count = result.scalar()
            print(f"Users count: {user_count}")
            
            # Check for common issues
            if div_count == 0:
                print("No divisions found - this may cause issues")
                return False
                
            if user_count == 0:
                print("No users found - database is empty, users will be created on first login")
                
        print("Database health check passed")
        return True
        
    except Exception as e:
        print(f"Database diagnosis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("KPI Dashboard Database Setup Script")
    print("=" * 50)
    
    # Diagnose first
    if diagnose_database():
        # If diagnosis passes but setup is needed
        print("\nRunning database setup...")
        success = setup_database()
        
        if success:
            print("\nDatabase is ready for production!")
            sys.exit(0)
        else:
            print("\nDatabase setup failed")
            sys.exit(1)
    else:
        print("\nDatabase issues detected, running setup...")
        success = setup_database()
        
        if success:
            print("\nIssues resolved!")
            sys.exit(0)
        else:
            print("\nCould not resolve database issues")
            sys.exit(1)