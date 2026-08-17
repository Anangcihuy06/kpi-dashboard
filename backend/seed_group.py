import os
from sqlalchemy import text
from database import SessionLocal
from models import KPIRule, KPIRuleMetric, Division, User

db = SessionLocal()

def seed_group_rule():
    div_it = db.query(Division).filter(Division.code == "Technology").first()
    if not div_it:
        div_it = db.query(Division).filter(Division.code == "IT").first()
    
    if not div_it:
        print("No IT/Technology division found.")
        return

    # Check if rule exists
    group_name = "Digital Solution Development"
    group_id = "496"
    rule = db.query(KPIRule).filter(KPIRule.group_id == group_id).first()
    
    if not rule:
        rule = KPIRule(
            division_id=div_it.id,
            group_id=group_id,
            group_name=group_name,
            name="Digital Solution / IT Developer KPI Matrix",
            version=1,
            is_active=True
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        print(f"Created rule {rule.id}")
    else:
        # Update rule to feature_complexity
        rule.name = "Digital Solution / IT Developer KPI Matrix"
        # Delete old metrics
        db.query(KPIRuleMetric).filter(KPIRuleMetric.kpi_rule_id == rule.id).delete()
        db.commit()
        print(f"Updated rule {rule.id}")
        
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
    print("Metrics added successfully!")

if __name__ == "__main__":
    seed_group_rule()
