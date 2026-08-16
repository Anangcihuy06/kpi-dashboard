import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
from engine import evaluate_kpi_formula

logger = logging.getLogger(__name__)

class YearlyKPIEngine:
    @staticmethod
    def calculate_working_days(start_date: datetime, end_date: datetime) -> int:
        """Calculate number of working days (Mon-Fri) between two dates inclusive."""
        days = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Monday = 0, Sunday = 6
                days += 1
            current += timedelta(days=1)
        return days

    @staticmethod
    def scale_target(target: float, total_working_days: int, sprint_working_days: int = 10) -> float:
        """
        Scale a sprint-based target to a custom period based on working days.
        Default sprint length is 2 weeks (10 working days).
        """
        if sprint_working_days <= 0:
            return target
        
        daily_target = target / sprint_working_days
        scaled_target = daily_target * total_working_days
        return round(scaled_target, 2)

    @staticmethod
    def calculate_yearly_kpi(
        db: Session, 
        user_id: str, 
        start_date: datetime, 
        end_date: datetime, 
        aggregated_metrics: Dict[str, Any],
        team_max_sp: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate KPI scores over a specific period (e.g. yearly or YTD).
        For jira_sp: uses relative scoring against team's top performer.
        """
        # Find user's division and active rule
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
            
        division_id = user.division_id
        if not division_id:
            # Fallback to IT division
            default_div = db.query(models.Division).filter(models.Division.code == "IT").first()
            division_id = default_div.id if default_div else None
            
        if not division_id:
            return {"error": "Division not found"}
            
        rule = db.query(models.KPIRule).filter(
            models.KPIRule.division_id == division_id,
            models.KPIRule.is_active == True
        ).first()
        
        if not rule:
            return {"error": "Active KPI Rule not found"}
            
        metrics_defs = db.query(models.KPIRuleMetric).filter(
            models.KPIRuleMetric.kpi_rule_id == rule.id
        ).all()
        
        # Calculate working days in period
        working_days = YearlyKPIEngine.calculate_working_days(start_date, end_date)
        
        # Define the Pure Feature & Architectural Weight KPI Matrix Configuration (Story Points Excluded)
        four_pillars_config = [
            {
                "metric_key": "feature_complexity",
                "category": "ENGINEERING",
                "label": "Feature & Module Architectural Weight",
                "weight": 0.90,
                "formula_display": "min((complexity_pts / 300.0) * 100, 100.0)",
                "get_actual": lambda m: m.get("complexity_sp", 0.0),
                "calc_score": lambda act, m: min((float(act) / 300.0) * 100.0, 100.0),
                "get_vars": lambda m: {"target_complexity_pts": 300.0}
            },
            {
                "metric_key": "attendance",
                "category": "DISCIPLINE",
                "label": "Attendance & Punctuality",
                "weight": 0.10,
                "formula_display": "max((attendance_days / target_days) * 100 - (late_percentage * 0.5), 0)",
                "get_actual": lambda m: m.get("attendance_days", m.get("attendance", 0)),
                "calc_score": lambda act, m: max((float(act) / 261.0) * 100 - (float(m.get("late_percentage", 0.0)) * 0.5), 0.0),
                "get_vars": lambda m: {"target_days": 261.0, "late_percentage": round(m.get("late_percentage", 0.0), 2)}
            }
        ]

        breakdown = []
        total_score = 0.0
        total_weight = 0.0

        for p_cfg in four_pillars_config:
            actual_val = p_cfg["get_actual"](aggregated_metrics)
            score = p_cfg["calc_score"](actual_val, aggregated_metrics)
            
            # Apply cap at 100
            if score > 100.0:
                score = 100.0
            if score < 0.0:
                score = 0.0
                
            weight = p_cfg["weight"]
            weighted_score = score * weight
            
            total_score += weighted_score
            total_weight += weight
            
            breakdown.append({
                "metric_key": p_cfg["metric_key"],
                "category": p_cfg["category"],
                "label": p_cfg["label"],
                "actual_value": actual_val,
                "formula": p_cfg["formula_display"],
                "variables": p_cfg["get_vars"](aggregated_metrics),
                "calculated_score": round(score, 2),
                "weight": weight,
                "weighted_score": round(weighted_score, 2)
            })
                
        # Normalize score if weights don't add up to 1.0 (though they should)
        final_score = total_score / total_weight if total_weight > 0 else 0.0
        
        return {
            "period": {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "working_days": working_days
            },
            "kpi_rule_id": rule.id,
            "final_score": round(final_score, 2),
            "breakdown": breakdown
        }
