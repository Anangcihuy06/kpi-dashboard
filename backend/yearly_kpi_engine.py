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
            
        rule = None
        group_id = user.group_id
        
        # Try to find rule by group_id first
        if group_id:
            rule = db.query(models.KPIRule).filter(
                models.KPIRule.division_id == division_id,
                models.KPIRule.group_id == group_id,
                models.KPIRule.is_active == True
            ).first()
            
        # Fallback to division-level rule if no group rule exists
        if not rule:
            rule = db.query(models.KPIRule).filter(
                models.KPIRule.division_id == division_id,
                models.KPIRule.group_id.is_(None),
                models.KPIRule.is_active == True
            ).first()
        
        if not rule:
            return {"error": "Active KPI Rule not found"}
            
        metrics_defs = db.query(models.KPIRuleMetric).filter(
            models.KPIRuleMetric.kpi_rule_id == rule.id
        ).all()
        
        # Calculate working days in period
        working_days = YearlyKPIEngine.calculate_working_days(start_date, end_date)
        
        # Calculate dynamic metrics based on KPIRuleMetric definitions
        breakdown = []
        total_score = 0.0
        total_weight = 0.0

        for m_def in metrics_defs:
            try:
                # Retrieve all required variables from aggregated_metrics
                # We pass the entire aggregated_metrics dict as context to the evaluator
                
                # Special variable extraction for display/variables JSON based on rule
                variables_used = {}
                try:
                    if m_def.variables and isinstance(m_def.variables, dict):
                        for k in m_def.variables.keys():
                            if k in aggregated_metrics:
                                variables_used[k] = aggregated_metrics[k]
                    elif m_def.variables and isinstance(m_def.variables, str):
                        import json
                        var_keys = json.loads(m_def.variables).keys()
                        for k in var_keys:
                            if k in aggregated_metrics:
                                variables_used[k] = aggregated_metrics[k]
                except Exception as e:
                    logger.error(f"Error parsing variables for metric {m_def.metric_key}: {e}")

                # Merge variables from database into context
                # IMPORTANT: Variables from KPI rule take precedence over calculated company maxima
                eval_context = {}
                
                # First, add variables from the KPI rule configuration
                try:
                    if m_def.variables:
                        import json
                        vars_dict = m_def.variables if isinstance(m_def.variables, dict) else json.loads(m_def.variables)
                        for k, v in vars_dict.items():
                            eval_context[k] = v
                except Exception as e:
                    logger.error(f"Failed to merge variables for {m_def.metric_key}: {e}")
                
                # Then, add user's actual performance metrics, but skip maxima variables that are in config
                for k, v in aggregated_metrics.items():
                    # Only add if not already in eval_context (config variables take precedence)
                    if k not in eval_context:
                        eval_context[k] = v
                
                # CRITICAL FIX: Ensure formula variables exist in context
                missing_vars = []
                try:
                    import ast
                    tree = ast.parse(m_def.formula_expression, mode='eval')
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Name) and node.id not in eval_context:
                            missing_vars.append(node.id)
                    
                    if missing_vars:
                        logger.warning(f"Formula '{m_def.formula_expression}' missing variables: {missing_vars}")
                        
                        # Try to get missing variables from context if they match pattern
                        for var in missing_vars:
                            if var in aggregated_metrics:
                                eval_context[var] = aggregated_metrics[var]
                            elif "max_raw_sp" in aggregated_metrics and var in ["max_raw_sp", "max_jira_sp"]:
                                eval_context[var] = aggregated_metrics["max_raw_sp"]
                            elif "max_complexity_sp" in aggregated_metrics and var in ["max_complexity_sp", "max_complexity_pts"]:
                                eval_context[var] = aggregated_metrics["max_complexity_sp"]
                            elif "max_issues_cnt" in aggregated_metrics and var in ["max_issues_cnt", "max_jira_issues"]:
                                eval_context[var] = aggregated_metrics["max_issues_cnt"]
                            elif "max_founder_sp" in aggregated_metrics and var in ["max_founder_sp", "max_founder_pts"]:
                                eval_context[var] = aggregated_metrics["max_founder_sp"]
                            elif "max_" in var and "max_" in aggregated_metrics:
                                # Try to match based on pattern
                                for context_key, context_val in aggregated_metrics.items():
                                    if f"max_{var.replace('max_', '')}" == context_key or f"max_{var}" == context_key:
                                        eval_context[var] = context_val
                except Exception as e:
                    logger.error(f"Error parsing formula for missing variables: {e}")
                
                # Calculate score using formula engine
                raw_calculated_score = evaluate_kpi_formula(m_def.formula_expression, eval_context)
                
                # Apply cap score if defined - consistent with sprint engine
                cap_score = float(m_def.cap_score or 120.0)
                capped_score = min(max(raw_calculated_score, 0.0), cap_score)
                
                weight = float(m_def.weight)
                weighted_score = capped_score * weight
                
                total_score += weighted_score
                total_weight += weight
                
                # Fetch actual_value generically if exists
                actual_val = aggregated_metrics.get(m_def.metric_key, 0.0)
                
                breakdown.append({
                    "metric_key": m_def.metric_key,
                    "formula_used": m_def.formula_expression,
                    "input_variables": eval_context,
                    "raw_score": round(raw_calculated_score, 2),
                    "capped_score": round(capped_score, 2),
                    "weight": weight,
                    "weighted_score": round(weighted_score, 2)
                })
            except Exception as e:
                logger.error(f"Error calculating metric {m_def.metric_key}: {e}")
                
        # Return raw weighted sum (no normalization) to match sprint engine behavior
        # Matrix configurator expects weights to sum to 1.0, so this gives the correct final score
        final_score = total_score
        
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
