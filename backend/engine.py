import ast
import operator
from typing import Dict, Any, List

class SafeMathEvaluator(ast.NodeVisitor):
    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    ALLOWED_FUNCTIONS = {
        "min": min,
        "max": max,
        "abs": abs,
        "round": round
    }

    def __init__(self, context: Dict[str, float]):
        self.context = context

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)

        elif isinstance(node, (ast.Constant, ast.Num)):
            return float(node.value if isinstance(node, ast.Constant) else node.n)

        elif isinstance(node, ast.Name):
            if node.id in self.context:
                return float(self.context[node.id])
            raise ValueError(f"Variabel '{node.id}' tidak ditemukan dalam context metrics!")

        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in self.ALLOWED_OPERATORS:
                left = self.visit(node.left)
                right = self.visit(node.right)
                if op_type == ast.Div and right == 0:
                    return 0.0
                return self.ALLOWED_OPERATORS[op_type](left, right)
            raise ValueError(f"Operator biner '{op_type.__name__}' tidak diizinkan!")

        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in self.ALLOWED_OPERATORS:
                return self.ALLOWED_OPERATORS[op_type](self.visit(node.operand))
            raise ValueError(f"Operator unary '{op_type.__name__}' tidak diizinkan!")

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in self.ALLOWED_FUNCTIONS:
                func = self.ALLOWED_FUNCTIONS[node.func.id]
                args = [self.visit(arg) for arg in node.args]
                return float(func(*args))
            raise ValueError("Pemanggilan fungsi tidak dikenal/diizinkan!")

        else:
            raise ValueError(f"Sintaks tidak diizinkan dalam rumus: {type(node).__name__}")


def evaluate_kpi_formula(formula_str: str, context: Dict[str, float]) -> float:
    try:
        # Pre-process formula: strip spaces and check safety
        tree = ast.parse(formula_str, mode='eval')
        evaluator = SafeMathEvaluator(context)
        return float(evaluator.visit(tree))
    except Exception as e:
        print(f"[KPI Engine Error] Gagal mengevaluasi formula '{formula_str}': {str(e)}")
        return 0.0


class DynamicKPIEngine:
    @classmethod
    def calculate_sprint_score(
        cls, 
        rule_metrics_list: List[Dict[str, Any]], 
        raw_metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        
        total_kpi_score = 0.0
        breakdown = []
        
        for metric_rule in rule_metrics_list:
            metric_key = metric_rule["metric_key"]
            weight = float(metric_rule["weight"])
            formula = metric_rule["formula_expression"]
            variables = metric_rule.get("variables", {})
            cap_score = float(metric_rule.get("cap_score", 120.0))

            # Combine input raw metrics and static variables configured in the rule
            eval_context = {**raw_metrics, **variables}
            
            # Use safe parser
            raw_calculated_score = evaluate_kpi_formula(formula, eval_context)
            capped_score = min(max(raw_calculated_score, 0.0), cap_score)

            weighted_score = capped_score * weight
            total_kpi_score += weighted_score

            breakdown.append({
                "metric_key": metric_key,
                "formula_used": formula,
                "input_variables": eval_context,
                "raw_score": round(raw_calculated_score, 2),
                "capped_score": round(capped_score, 2),
                "weight": weight,
                "weighted_score": round(weighted_score, 2)
            })

        return {
            "final_sprint_score": round(total_kpi_score, 2),
            "breakdown": breakdown
        }
