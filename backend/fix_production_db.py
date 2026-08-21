#!/usr/bin/env python3
"""
Production Deployment Script
This script ensures database is properly set up for production deployment
"""

import sys
import os
from database import engine, Base, SessionLocal
from models import Division, User, IntegrationSetting
from sqlalchemy import text, inspect

def setup_production_database():
    """Set up database for production deployment"""
    print("=== Production Database Setup ===")
    
    try:
        # Check database connection
        print("1. Checking database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        print("✅ Database connection successful")
        
        # Create all tables
        print("2. Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created")

        # Unique constraints + query-path indexes (dedup leftovers first).
        # Same code path as main.py lifespan so deploy == local boot.
        print("2b. Running DB maintenance (unique constraints + indexes)...")
        from db_maintenance import run_db_maintenance
        for line in run_db_maintenance(engine):
            print(line)
        print("✅ DB maintenance done")
        
        # Verify critical tables exist
        print("3. Verifying critical tables...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        required_tables = ['divisions', 'users', 'sprints', 'kpi_rules', 'integration_settings']
        
        for table in required_tables:
            if table in tables:
                print(f"✅ Table '{table}' exists")
            else:
                print(f"❌ Table '{table}' missing!")
                return False
        
        db = SessionLocal()
        
        try:
            # Ensure IT division exists
            print("4. Setting up default divisions...")
            it_division = db.query(Division).filter(Division.code == "IT").first()
            if not it_division:
                print("Creating default IT division...")
                it_div = Division(code="IT", name="IT & Engineering", description="Information Technology Division")
                db.add(it_div)
                db.commit()
                print("✅ IT division created")
            else:
                print("✅ IT division already exists")
            
            # Ensure integration settings exist
            print("5. Setting up integration settings...")
            integration_settings = db.query(IntegrationSetting).first()
            if not integration_settings:
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
                print("✅ Integration settings created")
            else:
                print("✅ Integration settings already exist")
            
            # Final verification
            print("6. Final verification...")
            division_count = db.query(Division).count()
            integration_count = db.query(IntegrationSetting).count()
            
            print(f"✅ Database setup complete")
            print(f"   - Divisions: {division_count}")
            print(f"   - Integration Settings: {integration_count}")
            
            return True
            
        except Exception as e:
            db.rollback()
            print(f"❌ Error during data setup: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Critical database setup error: {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_database_issues():
    """Fix common database issues"""
    print("\n=== Fixing Common Issues ===")
    
    try:
        db = SessionLocal()
        
        # Fix missing divisions
        print("1. Checking for missing divisions...")
        if not db.query(Division).first():
            print("Creating default divisions...")
            divisions = [
                Division(code="IT", name="IT & Engineering", description="Information Technology Division"),
                Division(code="HR", name="Human Resources", description="Human Resources Division")
            ]
            for div in divisions:
                db.add(div)
            db.commit()
            print(f"✅ Created {len(divisions)} default divisions")
        else:
            print("✅ Divisions exist")
        
        # Fix missing integration settings
        print("2. Checking for missing integration settings...")
        if not db.query(IntegrationSetting).first():
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
            print("✅ Integration settings created")
        else:
            print("✅ Integration settings exist")
        
        # Ensure Technology Division KPI rule has feature_complexity
        print("3. Checking Technology Division KPI Rule...")
        from models import KPIRule, KPIRuleMetric
        
        # Find IT/Technology division
        it_div = db.query(Division).filter(Division.code.in_(["IT", "Technology"])).first()
        if it_div:
            # Find default rule (group_id is None)
            rule = db.query(KPIRule).filter(
                KPIRule.division_id == it_div.id,
                KPIRule.group_id.is_(None)
            ).first()
            
            if not rule:
                print("Creating default KPI Rule for Technology division...")
                rule = KPIRule(
                    division_id=it_div.id,
                    name="IT Developer KPI Matrix",
                    version=1,
                    is_active=True
                )
                db.add(rule)
                db.commit()
                db.refresh(rule)
                
            # Check if it has feature_complexity
            has_fc = db.query(KPIRuleMetric).filter(
                KPIRuleMetric.kpi_rule_id == rule.id,
                KPIRuleMetric.metric_key == "feature_complexity"
            ).first()
            
            if not has_fc:
                print("Adding feature_complexity metric to Technology division rule...")
                # Delete existing metrics
                db.query(KPIRuleMetric).filter(KPIRuleMetric.kpi_rule_id == rule.id).delete()
                db.commit()
                
                # Add new metrics
                m1 = KPIRuleMetric(
                    kpi_rule_id=rule.id,
                    metric_key="feature_complexity",
                    category="ENGINEERING",
                    weight=0.90,
                    calc_type="FORMULA",
                    formula_expression="min((complexity_sp / target_complexity_pts) * 100, 100)",
                    variables={"target_complexity_pts": 300, "max_c": 5, "max_i": 5, "max_s": 5, "max_r": 3, "max_o": 2},
                    cap_score=100.0
                )
                m2 = KPIRuleMetric(
                    kpi_rule_id=rule.id,
                    metric_key="attendance",
                    category="DISCIPLINE",
                    weight=0.10,
                    calc_type="FORMULA",
                    formula_expression="max((attendance_days / target_days) * 100 - (late_percentage * 0.5), 0)",
                    variables={"target_days": 261, "late_percentage": 5},
                    cap_score=100.0
                )
                db.add_all([m1, m2])
                db.commit()
                print("✅ Technology Division KPI Rule updated with feature_complexity")
            else:
                print("✅ Technology Division KPI Rule already has feature_complexity")
                
        db.close()
        print("✅ Issues fixed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing issues: {e}")
        return False

if __name__ == "__main__":
    print("Production Database Setup & Fix Script")
    print("=" * 50)
    
    # Try setup first
    setup_success = setup_production_database()
    
    if setup_success:
        print("\n✅ Production database is ready!")
        sys.exit(0)
    else:
        print("\n⚠️ Setup failed, trying fixes...")
        fix_success = fix_database_issues()
        
        if fix_success:
            print("\n✅ Issues resolved, database is ready!")
            sys.exit(0)
        else:
            print("\n❌ Could not resolve database issues")
            sys.exit(1)