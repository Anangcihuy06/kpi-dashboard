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

    ALLOWED_COMPARISONS = {
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
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
            # Support conditional function: if(condition, value_if_true, value_if_false)
            if isinstance(node.func, ast.Name) and node.func.id == "if":
                if len(node.args) != 3:
                    raise ValueError("Fungsi 'if' membutuhkan 3 argumen: if(kondisi, nilai_benar, nilai_salah)")
                cond = self.visit(node.args[0])
                return float(self.visit(node.args[1] if cond else node.args[2]))
            raise ValueError("Pemanggilan fungsi tidak dikenal/diizinkan!")

        elif isinstance(node, ast.Compare):
            if len(node.comparators) != 1 or len(node.ops) != 1:
                raise ValueError("Perbandingan berantai tidak diizinkan!")
            op_type = type(node.ops[0])
            if op_type not in self.ALLOWED_COMPARISONS:
                raise ValueError(f"Operator perbandingan '{op_type.__name__}' tidak diizinkan!")
            left = self.visit(node.left)
            right = self.visit(node.comparators[0])
            return float(self.ALLOWED_COMPARISONS[op_type](left, right))

        elif isinstance(node, ast.IfExp):
            cond = self.visit(node.test)
            return float(self.visit(node.body if cond else node.orelse))

        elif isinstance(node, ast.BoolOp):
            values = [self.visit(v) for v in node.values]
            if isinstance(node.op, ast.And):
                result = True
                for v in values:
                    result = result and bool(v)
                return float(result)
            elif isinstance(node.op, ast.Or):
                result = False
                for v in values:
                    result = result or bool(v)
                return float(result)
            raise ValueError(f"Operator boolean '{type(node.op).__name__}' tidak diizinkan!")

        else:
            raise ValueError(f"Sintaks tidak diizinkan dalam rumus: {type(node).__name__}")


def _preprocess_if_calls(formula_str: str) -> str:
    """Convert AI-generated `if(cond, a, b)` calls into valid Python ternary.

    `if` is a reserved Python keyword, so `if(x > 1, 10, 0)` fails ast.parse.
    We rewrite it to `(10 if (x > 1) else 0)` so the SafeMathEvaluator can handle
    it through ast.IfExp.
    """
    out = []
    i = 0
    n = len(formula_str)
    while i < n:
        c = formula_str[i]
        # Look for `if(` that is a function call (not part of identifier / not ternary)
        if c == 'i' and i + 2 < n and formula_str[i:i+3] == 'if(':
            # find matching close paren
            depth = 1
            j = i + 3
            while j < n and depth > 0:
                if formula_str[j] == '(':
                    depth += 1
                elif formula_str[j] == ')':
                    depth -= 1
                j += 1
            if depth == 0:
                inner = formula_str[i+3:j-1]
                parts = _split_top_level_commas(inner)
                if len(parts) == 3:
                    cond, val_true, val_false = parts
                    out.append(f"({val_true} if ({cond}) else {val_false})")
                    i = j
                    continue
                # malformed -> leave as-is (will fail parse, caught later)
        out.append(c)
        i += 1
    return "".join(out)


def _split_top_level_commas(s: str) -> list:
    """Split a string on commas that are not nested inside () [] {}."""
    parts = []
    depth = 0
    current = []
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    parts.append("".join(current).strip())
    return parts


def evaluate_kpi_formula(formula_str: str, context: Dict[str, float]) -> float:
    try:
        # Pre-process formula: strip spaces and check safety
        processed = _preprocess_if_calls(formula_str)
        tree = ast.parse(processed, mode='eval')
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
