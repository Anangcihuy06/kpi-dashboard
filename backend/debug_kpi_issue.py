#!/usr/bin/env python3
"""
Fix KPI Calculation Issues
This script identifies and fixes calculation inconsistencies between configurator and dashboard
"""

import sys
from database import SessionLocal
import models
from yearly_kpi_engine import YearlyKPIEngine
from engine import evaluate_kpi_formula
from datetime import datetime

def check_current_issue(user_nik, year=2026):
    """Check what's happening with a specific user's KPI calculation"""
    print(f"=== Analyzing KPI Calculation for {user_nik} ({year}) ===")
    
    db = SessionLocal()
    
    try:
        # Get user
        user = db.query(models.User).filter(models.User.nik == user_nik).first()
        if not user:
            print(f"User with NIK {user_nik} not found")
            return
            
        print(f"User: {user.full_name} (Division: {user.division_id}, Group: {user.group_id})")
        
        # Get active rule
        rule = db.query(models.KPIRule).filter(
            models.KPIRule.division_id == user.division_id,
            models.KPIRule.group_id == user.group_id,
            models.KPIRule.is_active == True
        ).first()
        
        if not rule:
            rule = db.query(models.KPIRule).filter(
                models.KPIRule.division_id == user.division_id,
                models.KPIRule.group_id.is_(None),
                models.KPIRule.is_active == True
            ).first()
        
        if not rule:
            print("No active KPI rule found!")
            return
            
        print(f"Rule: {rule.name}")
        
        # Get metrics
        metrics = db.query(models.KPIRuleMetric).filter(
            models.KPIRuleMetric.kpi_rule_id == rule.id
        ).all()
        
        print(f"\n=== Metrics Configuration ===")
        for m in metrics:
            print(f"\n{m.metric_key} (weight={m.weight}, cap={m.cap_score})")
            print(f"  Formula: {m.formula_expression}")
            print(f"  Variables: {m.variables}")
            
            # Test formula with sample data
            test_context = {
                "attendance_days": 200,
                "target_days": 261,
                "late_percentage": 5,
                "raw_jira_sp": 80,
                "max_raw_sp": 100,
                "complexity_sp": 90,
                "max_complexity_sp": 100,
                "jira_issues_completed": 12,
                "max_issues_cnt": 30,
                "founder_sp_credit": 40,
                "max_founder_sp": 50
            }
            
            try:
                score = evaluate_kpi_formula(m.formula_expression, test_context)
                print(f"  Test calculation result: {score}")
            except Exception as e:
                print(f"  Formula test failed: {e}")
        
        # Get actual yearly data
        from_date = datetime(year, 1, 1)
        to_date = datetime(year, 12, 31)
        
        # Calculate company maxima for relative scoring
        all_users = db.query(models.User).filter(models.User.is_active == True).all()
        
        max_raw_sp = 0.0
        max_complexity_sp = 0.0
        max_issues_cnt = 0
        max_founder_sp = 0.0
        
        for u in all_users:
            jira_id = db.query(models.EmployeeIdentity).filter(
                models.EmployeeIdentity.user_id == u.id,
                models.EmployeeIdentity.source == 'jira'
            ).first()
            
            if jira_id and jira_id.external_user_id:
                all_raw_jiras = db.query(models.RawJiraIssue).filter(
                    models.RawJiraIssue.assignee_account_id == jira_id.external_user_id
                ).all()
                
                for ji in all_raw_jiras:
                    status_lower = (ji.status or "").lower()
                    if status_lower in ["done", "resolved", "ready to release", "ready for uat", "uat (user)", "ready for qa", "in qa"]:
                        max_raw_sp += float(ji.story_points or 0.0)
                        max_issues_cnt += 1
                        # Estimate complexity as fallback
                        max_complexity_sp = max(max_complexity_sp, 100)
                        
            from founder_engine import get_founder_credits_for_user
            max_founder_sp = max(max_founder_sp, get_founder_credits_for_user(u.id, year))
        
        print(f"\n=== Company Maxima for {year} ===")
        print(f"max_raw_sp: {max_raw_sp}")
        print(f"max_complexity_sp: {max_complexity_sp}")
        print(f"max_issues_cnt: {max_issues_cnt}")
        print(f"max_founder_sp: {max_founder_sp}")
        
        # Get user's actual metrics
        working_days = YearlyKPIEngine.calculate_working_days(from_date, to_date)
        
        user_metrics = {
            "attendance_days": 0,
            "target_days": working_days,
            "late_percentage": 0,
            "raw_jira_sp": 0.0,
            "complexity_sp": 0.0,
            "jira_issues_completed": 0,
            "founder_sp_credit": 0.0,
            "max_raw_sp": max_raw_sp,
            "max_complexity_sp": max_complexity_sp,
            "max_issues_cnt": max_issues_cnt,
            "max_founder_sp": max_founder_sp
        }
        
        # Get user's actual performance data using user_id
        daily_kpis = db.query(models.KPIEmployeeDaily).filter(
            models.KPIEmployeeDaily.user_id == user.id,
            models.KPIEmployeeDaily.date >= from_date,
            models.KPIEmployeeDaily.date <= to_date
        ).all()
        
        if daily_kpis:
            user_metrics["attendance_days"] = sum(d.attendance_days for d in daily_kpis)
            user_metrics["late_percentage"] = (sum(d.late_count for d in daily_kpis) / working_days * 100) if working_days > 0 else 0
            user_metrics["raw_jira_sp"] = sum(d.story_points_completed for d in daily_kpis)
            user_metrics["complexity_sp"] = sum(d.story_points_completed for d in daily_kpis)  # Using SP as proxy for complexity
            user_metrics["jira_issues_completed"] = sum(d.issue_completed for d in daily_kpis)
            user_metrics["founder_sp_credit"] = 0.0  # Not stored in daily KPI - need separate query
        
        print(f"\n=== User's Actual Metrics ===")
        for key, value in user_metrics.items():
            if isinstance(value, float):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")
        
        # Test each metric calculation
        print(f"\n=== Metric-by-Metric Calculation ===")
        total_score = 0.0
        total_weight = 0.0
        
        for m_def in metrics:
            try:
                eval_context = dict(user_metrics)
                
                # Add variables from rule (actual metrics take precedence)
                try:
                    if m_def.variables:
                        from engine import merge_rule_variables
                        eval_context = merge_rule_variables(eval_context, m_def.variables)
                except Exception as e:
                    print(f"  Variables error: {e}")
                
                # Calculate score
                score = evaluate_kpi_formula(m_def.formula_expression, eval_context)
                capped_score = min(max(score, 0.0), float(m_def.cap_score))
                weighted_score = capped_score * float(m_def.weight)
                
                total_score += weighted_score
                total_weight += float(m_def.weight)
                
                print(f"{m_def.metric_key}:")
                print(f"  Raw score: {score:.2f}")
                print(f"  Capped score: {capped_score:.2f}")
                print(f"  Weight: {float(m_def.weight)}")
                print(f"  Weighted score: {weighted_score:.2f}")
                
            except Exception as e:
                print(f"{m_def.metric_key}: ERROR - {e}")
        
        print(f"\n=== Final Results ===")
        print(f"Total weighted score: {total_score:.2f}")
        print(f"Total weight: {total_weight:.2f}")
        print(f"Final score (normalized): {total_score / total_weight if total_weight > 0 else 0:.2f}")
        print(f"Final score (raw weighted sum): {total_score:.2f}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    nik = sys.argv[1] if len(sys.argv) > 1 else "01.05.13.999"
    year = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
    check_current_issue(nik, year)