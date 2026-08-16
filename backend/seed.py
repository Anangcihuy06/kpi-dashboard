from datetime import datetime, timedelta
from database import engine, SessionLocal, Base
from models import Division, User, Sprint, KPIRule, KPIRuleMetric, RawMetricsData, SprintKPIScore, AttendanceRecord, IntegrationSetting
from engine import DynamicKPIEngine
from sync_service import get_working_days, generate_attendance_data_for_user
from encrypt import encrypt_val

def seed_data():
    # Re-create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # 1. Create Divisions
    it_div = Division(code="IT", name="IT & Engineering", description="Divisi Software Development")
    hr_div = Division(code="HR", name="Human Resources", description="Divisi Kepegawaian")
    db.add_all([it_div, hr_div])
    db.commit()
    
    db.refresh(it_div)
    db.refresh(hr_div)
    
    # 2. Create NO Sprints - will be synced from Jira
    # No mock sprint data created - will rely on Jira sync
    
    # 3. Add integration settings template (empty - user must fill)
    integration_settings = IntegrationSetting(
        jira_url="",
        jira_email="",
        jira_token_encrypted=None,
        jira_board_ids=[],
        default_jira_board_id="",
        jira_sp_field="customfield_10016",
        gitlab_url="https://gitlab.com",
        gitlab_token_encrypted=None
    )
    db.add(integration_settings)
    db.commit()
    
    # 3. Create Sprints (will be populated by Jira sync - no dummy data)
    
    # 3. Create KPI Rules for IT Division (REBALANCED with attendance)
    kpi_rule = KPIRule(division_id=it_div.id, name="IT Developer KPI Matrix v2", version=1, is_active=True)
    db.add(kpi_rule)
    db.commit()
    db.refresh(kpi_rule)
    
    # Metric 1: Jira Story Points (40%)
    metric1 = KPIRuleMetric(
        kpi_rule_id=kpi_rule.id,
        metric_key="jira_sp",
        weight=0.40,
        calc_type="FORMULA",
        formula_expression="min((jira_sp / target_sp) * 100, 120)",
        variables={"target_sp": 20},
        cap_score=120.0
    )
    # Metric 2: GitLab Merge Requests (40%)
    metric2 = KPIRuleMetric(
        kpi_rule_id=kpi_rule.id,
        metric_key="gitlab_mr",
        weight=0.40,
        calc_type="FORMULA",
        formula_expression="(gitlab_mr_merged / target_mr) * 100",
        variables={"target_mr": 5},
        cap_score=100.0
    )
    # Metric 3: Attendance Score (20%)
    metric3 = KPIRuleMetric(
        kpi_rule_id=kpi_rule.id,
        metric_key="attendance",
        weight=0.20,
        calc_type="FORMULA",
        formula_expression="max((attendance_days / target_days) * 100 - (late_percentage * 0.5), 0)",
        variables={"target_days": 10},
        cap_score=100.0
    )
    db.add_all([metric1, metric2, metric3])
    db.commit()
    
    # 4. Create Users (Hierarchical Structure)
    # Senior Manager (Hartono Karmayana)
    spv_sr_mgr = User(
        id="8515",
        nik="01.05.13.999",
        employee_id="4820",
        full_name="Hartono Karmayana",
        email="hartono@atibusinessgroup.com",
        roles=["MANAGER"],
        has_subordinates=True,
        division_id=it_div.id,
        supervisor_id=None
    )
    db.add(spv_sr_mgr)
    db.commit()
    
    # Manager (Ryan Fadilla Poernama - our main login test user)
    ryan = User(
        id="482",
        nik="01.05.13.500",
        employee_id="4914",
        full_name="Ryan Fadilla Poernama",
        email="ryan.fadilla@atibusinessgroup.com",
        roles=["MANAGER", "ROLE_ADMIN"],
        has_subordinates=True,
        division_id=it_div.id,
        supervisor_id="8515"
    )
    db.add(ryan)
    db.commit()

    # 5. Metrics list (matching new 3-metric structure)
    metrics_list = [
        {"metric_key": "jira_sp", "weight": 0.40, "formula_expression": "min((jira_sp / target_sp) * 100, 120)", "variables": {"target_sp": 20}, "cap_score": 120.0},
        {"metric_key": "gitlab_mr", "weight": 0.40, "formula_expression": "(gitlab_mr_merged / target_mr) * 100", "variables": {"target_mr": 5}, "cap_score": 100.0},
        {"metric_key": "attendance", "weight": 0.20, "formula_expression": "max((attendance_days / target_days) * 100 - (late_percentage * 0.5), 0)", "variables": {"target_days": 10}, "cap_score": 100.0}
    ]

    # 6. Generate attendance data + raw metrics for Ryan (will be created after Jira sync)
    # Note: Skipping sprint data creation - will be populated by Jira sync
    print("\nDatabase seeding completed successfully! (No sprint data - will sync from Jira)")
    print("Please configure Jira integration settings in the admin panel.")
    db.close()

if __name__ == "__main__":
    seed_data()
