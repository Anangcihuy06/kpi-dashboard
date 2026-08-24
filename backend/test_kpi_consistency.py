#!/usr/bin/env python3
"""
Test KPI Calculation Consistency
Compare yearly vs sprint calculation logic
"""

from database import engine, SessionLocal
import models
from engine import DynamicKPIEngine, evaluate_kpi_formula
from yearly_kpi_engine import YearlyKPIEngine
from datetime import datetime, timedelta

def test_calculation_consistency():
    """Test if yearly and sprint calculations match"""
    print("=== Testing KPI Calculation Consistency ===")
    
    db = SessionLocal()
    
    try:
        # Get a user with KPI data
        user = db.query(models.User).filter(models.User.nik == "01.05.13.999").first()
        if not user:
            print("Test user not found")
            return
            
        print(f"Testing with user: {user.full_name} ({user.nik})")
        
        # Get active rules
        rule = db.query(models.KPIRule).filter(
            models.KPIRule.division_id == user.division_id,
            models.KPIRule.is_active == True
        ).first()
        
        if not rule:
            print("No active rules found")
            return
            
        print(f"Using rule: {rule.name}")
        
        # Get rule metrics
        metrics = db.query(models.KPIRuleMetric).filter(
            models.KPIRuleMetric.kpi_rule_id == rule.id
        ).all()
        
        print(f"Found {len(metrics)} metrics")
        for m in metrics:
            print(f"  - {m.metric_key}: weight={m.weight}, formula={m.formula_expression}")
        
        # Test sample calculation
        print("\n=== Testing Sample Calculation ===")
        
        sample_metrics = {
            "attendance_days": 200,
            "target_days": 260,
            "late_percentage": 5,
            "complexity_sp": 150,
            "target_complexity_pts": 300,
            "raw_jira_sp": 120,
            "jira_issues_completed": 10
        }
        
        # Calculate using DynamicKPIEngine
        dynamic_result = DynamicKPIEngine.calculate_sprint_score(
            [m.__dict__ for m in metrics],
            sample_metrics
        )
        
        print("DynamicKPIEngine Result:")
        print(f"  Final Score: {dynamic_result['final_sprint_score']}")
        print(f"  Breakdown:")
        for b in dynamic_result['breakdown']:
            print(f"    {b['metric_key']}: weighted={b['weighted_score']}, raw={b['raw_score']}")
            
        # Calculate using YearlyKPIEngine (simulated)
        yearly_result = YearlyKPIEngine.calculate_yearly_kpi(
            db=db,
            user_id=user.id,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 12, 31),
            aggregated_metrics=sample_metrics,
            team_max_sp=0.0
        )
        
        print("\nYearlyKPIEngine Result:")
        print(f"  Final Score: {yearly_result['final_score']}")
        print(f"  Breakdown:")
        for b in yearly_result['breakdown']:
            print(f"    {b['metric_key']}: weighted={b['weighted_score']}, raw={b['raw_score']}")
        
        # Compare results
        print("\n=== Comparison ===")
        dynamic_final = dynamic_result['final_sprint_score']
        yearly_final = yearly_result['final_score']
        
        if abs(dynamic_final - yearly_final) < 0.01:
            print(f"✅ Scores match! ({dynamic_final} ≈ {yearly_final})")
        else:
            print(f"❌ Scores mismatch! ({dynamic_final} vs {yearly_final})")
            print(f"   Difference: {abs(dynamic_final - yearly_final)}")
        
        # Check breakdown structure
        print("\n=== Breakdown Structure Comparison ===")
        dynamic_keys = set(dynamic_result['breakdown'][0].keys()) if dynamic_result['breakdown'] else set()
        yearly_keys = set(yearly_result['breakdown'][0].keys()) if yearly_result['breakdown'] else set()
        
        print(f"DynamicKPIEngine breakdown keys: {dynamic_keys}")
        print(f"YearlyKPIEngine breakdown keys: {yearly_keys}")
        
        missing_keys = dynamic_keys - yearly_keys
        extra_keys = yearly_keys - dynamic_keys
        
        if missing_keys:
            print(f"❌ Missing keys in YearlyKPIEngine: {missing_keys}")
        if extra_keys:
            print(f"⚠️  Extra keys in YearlyKPIEngine: {extra_keys}")
            
        if not missing_keys and not extra_keys:
            print("✅ Breakdown structures match!")
        
        # Check individual metric calculations
        print("\n=== Individual Metric Calculation Test ===")
        for m in metrics:
            print(f"\nTesting metric: {m.metric_key}")
            
            # Build eval context
            eval_context = dict(sample_metrics)
            try:
                if m.variables:
                    from engine import merge_rule_variables
                    eval_context = merge_rule_variables(eval_context, m.variables)
            except Exception as e:
                print(f"  Error parsing variables: {e}")
                continue
            
            # Calculate score
            score = evaluate_kpi_formula(m.formula_expression, eval_context)
            capped_score = min(max(score, 0.0), float(m.cap_score))
            weighted_score = capped_score * float(m.weight)
            
            print(f"  Formula: {m.formula_expression}")
            print(f"  Raw score: {score}")
            print(f"  Capped score: {capped_score}")
            print(f"  Weight: {m.weight}")
            print(f"  Weighted score: {weighted_score}")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_calculation_consistency()