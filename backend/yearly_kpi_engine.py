import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
from engine import evaluate_kpi_formula

logger = logging.getLogger(__name__)

# Map config metric_key -> aggregated raw input metric shown as "Nilai Raw"
METRIC_RAW_KEY_MAP = {
    "feature_complexity": "complexity_sp",
    "jira_sp": "jira_sp",
    "jira_issues_completed": "jira_issues_completed",
    "gitlab_mr": "gitlab_mr_merged",
    "gitlab_commits": "gitlab_commits",
    "attendance": "attendance_days",
}


def _resolve_formula_raw_value(formula_expression: str, metrics: Dict[str, Any], eval_context: Dict[str, Any]) -> float:
    """Resolve the raw measure behind an AI-generated formula metric.

    For metric_keys not mapped in METRIC_RAW_KEY_MAP (e.g. `if(jira_sp > 300, 10, 0)`),
    extract the variable names from the formula and return the first real performance
    metric so the dashboard "Nilai Raw" column shows actual data instead of 0.
    """
    try:
        import ast
        from engine import _preprocess_if_calls
        tree = ast.parse(_preprocess_if_calls(formula_expression), mode='eval')
        vars_in_formula = [
            node.id for node in ast.walk(tree)
            if isinstance(node, ast.Name) and node.id not in ("min", "max", "abs", "round")
        ]
    except Exception:
        vars_in_formula = []

    priority = ("jira_sp", "raw_jira_sp", "complexity_sp", "jira_issues_completed",
                "attendance_days", "gitlab_commits", "gitlab_mr", "worklog_hours",
                "founder_sp_credit")
    for var in vars_in_formula:
        if var in priority and var in metrics:
            val = metrics.get(var, 0.0)
            return round(float(val), 2) if isinstance(val, (int, float)) else 0.0
    for var in vars_in_formula:
        if var.startswith(("target_", "max_", "min_")):
            continue
        if var in metrics:
            val = metrics.get(var, 0.0)
            return round(float(val), 2) if isinstance(val, (int, float)) else 0.0
    return 0.0

def get_rule_and_metrics_for_user(db, user):
    """
    Resolve the active KPI rule for a user (group-level first, then division-level)
    together with its metric definitions. Single source of truth for rule lookup.
    """
    division_id = user.division_id
    if not division_id:
        default_div = db.query(models.Division).filter(models.Division.code == "IT").first()
        division_id = default_div.id if default_div else None
    if not division_id:
        return None, []

    group_id = user.group_id
    rule = None
    if group_id:
        rule = db.query(models.KPIRule).filter(
            models.KPIRule.division_id == division_id,
            models.KPIRule.group_id == group_id,
            models.KPIRule.is_active == True
        ).first()

    if not rule:
        rule = db.query(models.KPIRule).filter(
            models.KPIRule.division_id == division_id,
            models.KPIRule.group_id.is_(None),
            models.KPIRule.is_active == True
        ).first()

    if not rule:
        return None, []

    metrics_defs = db.query(models.KPIRuleMetric).filter(
        models.KPIRuleMetric.kpi_rule_id == rule.id
    ).all()
    return rule, metrics_defs

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

        rule, metrics_defs = get_rule_and_metrics_for_user(db, user)
        if not rule:
            return {"error": "Active KPI Rule not found"}

        if not metrics_defs:
            return {"error": "No metrics configured for the active KPI rule"}
        
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
                
                # First, add user's actual performance metrics
                eval_context.update(aggregated_metrics)
                
                # Then, add rule config variables that are not already present
                # (actual metrics win over declarative default_values)
                try:
                    if m_def.variables:
                        from engine import merge_rule_variables
                        eval_context = merge_rule_variables(eval_context, m_def.variables)
                except Exception as e:
                    logger.error(f"Failed to merge variables for {m_def.metric_key}: {e}")
                
                # CRITICAL FIX: Ensure formula variables exist in context
                missing_vars = []
                try:
                    import ast
                    from engine import _preprocess_if_calls
                    tree = ast.parse(_preprocess_if_calls(m_def.formula_expression), mode='eval')
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
                raw_key = METRIC_RAW_KEY_MAP.get(m_def.metric_key, m_def.metric_key)
                if raw_key in aggregated_metrics:
                    actual_val = aggregated_metrics.get(raw_key, aggregated_metrics.get(m_def.metric_key, 0.0))
                else:
                    # AI-generated formula metric: resolve the raw measure behind the
                    # formula (e.g. jira_sp) so the "Nilai Raw" column shows real data.
                    actual_val = _resolve_formula_raw_value(
                        m_def.formula_expression, aggregated_metrics, eval_context)
                
                breakdown.append({
                    "metric_key": m_def.metric_key,
                    "formula": m_def.formula_expression,
                    "formula_used": m_def.formula_expression,
                    "variables": eval_context,
                    "input_variables": eval_context,
                    "actual_value": round(actual_val, 2),
                    "raw_score": round(raw_calculated_score, 2),
                    "calculated_score": round(capped_score, 2),
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
