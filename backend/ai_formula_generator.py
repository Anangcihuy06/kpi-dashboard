# NEW: AI INDICATOR CREATOR - AI Formula Generation Service
import os
import json
import logging
import time
import httpx
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from division_variables import (
    get_division_variables,
    get_division_example_prompts,
    get_division_common_targets,
    get_available_variables_by_type
)

logger = logging.getLogger("ai_formula_generator")

# AI Request/Response Models
class AIFormulaRequest(BaseModel):
    user_id: str
    user_name: str
    user_role: str
    has_subordinates: bool
    division_id: str
    division_name: str
    division_code: str
    group_id: Optional[str]
    group_name: Optional[str]
    creation_scope: str  # "division", "group", "personal"
    indicator_description: str

class AIFormulaResponse(BaseModel):
    status: str
    formula: Optional[str]
    variables: Optional[Dict[str, Any]]
    cap_score: Optional[float]
    alternatives: Optional[List[str]]
    explanation: Optional[str]
    validation: Optional[Dict[str, Any]]
    error: Optional[str]

class AIFeatureScorer:
    """
    AI-powered formula generator for KPI indicators
    Uses Z.AI GLM Coding Plan API with GLM model
    """
    
    DEFAULT_BASE_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize AI Feature Scorer
        
        Args:
            api_key: Z.AI API key (defaults to environment variable)
            model: Model to use (defaults to glm-5.3)
        """
        self.api_key = api_key or os.getenv("ZAI_API_KEY")
        self.base_url = os.getenv("ZAI_BASE_URL") or self.DEFAULT_BASE_URL
        self.model = model or os.getenv("ZAI_MODEL") or "glm-5.3"
        self.enabled = bool(self.api_key and self.api_key.strip())
        
        if not self.enabled:
            logger.warning("AI Formula Generator disabled: ZAI_API_KEY not set")
    
    def generate_formula(self, request: AIFormulaRequest) -> AIFormulaResponse:
        """
        Generate KPI formula from natural language description
        
        Args:
            request: AI formula generation request with user context
        
        Returns:
            AI formula response with generated formula, variables, and validation
        """
        if not self.enabled:
            return self._get_fallback_response(request)
        
        try:
            # Build AI context
            ai_context = self._build_ai_context(request)
            
            # Generate AI prompt
            prompt = self._build_ai_prompt(request, ai_context)
            
            # Call Z.AI Coding Plan API
            response_data = self._call_ai_api(prompt)
            
            if not response_data or response_data.get("status") == "error":
                return self._get_fallback_response(request, response_data.get("error", "AI API call failed"))
            
            # Parse AI response
            formula_data = response_data.get("data", {})
            
            # Validate generated formula
            validation = self._validate_formula(formula_data.get("formula", ""), ai_context)
            
            return AIFormulaResponse(
                status="success",
                formula=formula_data.get("formula"),
                variables=formula_data.get("variables", {}),
                cap_score=formula_data.get("cap_score", 100.0),
                alternatives=formula_data.get("alternatives", []),
                explanation=formula_data.get("explanation", ""),
                validation=validation,
                error=None
            )
            
        except Exception as e:
            logger.error(f"AI formula generation failed: {str(e)}")
            return self._get_fallback_response(request, str(e))
    
    def _build_ai_context(self, request: AIFormulaRequest) -> Dict[str, Any]:
        """
        Build context object for AI formula generation
        
        Args:
            request: AI formula generation request
        
        Returns:
            Context dictionary with division-specific information
        """
        # Get division-specific variables
        division_variables = get_division_variables(request.division_code)
        
        # Get common targets for division
        common_targets = get_division_common_targets(request.division_code)
        
        # Get available variables based on user role
        available_variables = []
        for var_type in ["core", "advanced", "ai_suggested"]:
            vars_of_type = get_available_variables_by_type(
                request.division_code, 
                var_type, 
                request.user_role
            )
            available_variables.extend(vars_of_type)
        
        return {
            "user": {
                "id": request.user_id,
                "name": request.user_name,
                "role": request.user_role,
                "has_subordinates": request.has_subordinates,
                "creation_scope": request.creation_scope
            },
            "division": {
                "id": request.division_id,
                "name": request.division_name,
                "code": request.division_code
            },
            "group": {
                "id": request.group_id,
                "name": request.group_name
            } if request.group_id else None,
            "available_variables": available_variables,
            "common_targets": common_targets,
            "division_variables": division_variables,
            "supported_functions": ["min", "max", "abs", "round"],
            "supported_operators": ["+", "-", "*", "/", "%", "**"]
        }
    
    def _build_ai_prompt(self, request: AIFormulaRequest, context: Dict[str, Any]) -> str:
        """
        Build AI prompt for formula generation
        
        Args:
            request: AI formula generation request
            context: AI context object
        
        Returns:
            Formatted AI prompt
        """
        # Format available variables for AI
        variables_list = []
        for var in context["available_variables"]:
            var_info = f"- `{var['name']}`: {var['description']}"
            if var.get("unit"):
                var_info += f" (unit: {var['unit']})"
            if var.get("default_value") is not None:
                var_info += f" [default: {var['default_value']}]"
            variables_list.append(var_info)
        
        variables_text = "\n".join(variables_list)
        
        # Format common targets
        targets_text = "\n".join([
            f"- `{target}`: {value}" 
            for target, value in context["common_targets"].items()
        ])
        
        prompt = f"""
    You are an expert KPI formula generator for the KPI Dashboard system. Generate mathematical formulas from natural language descriptions.

    ## User Context
    - User: {request.user_name} ({request.user_role})
    - Division: {request.division_name} ({request.division_code})
    - Group: {request.group_name or 'N/A'}
    - Creation Scope: {request.creation_scope}
    - Has Subordinates: {request.has_subordinates}

    ## Division Context
    Division: {request.division_name}
    Focus: {self._get_division_focus(request.division_code)}

    ## Available Variables
    {variables_text}

    ## Common Targets for {request.division_name}
    {targets_text}

    ## Supported Mathematical Operations
    - Operators: +, -, *, /, %, **
    - Functions: min(), max(), abs(), round()
    - Comparison: ==, !=, <, <=, >, >=
    - Logical: and, or, not

    ## Formula Requirements
    1. Use only the available variables listed above
    2. Include target values from common targets when applicable
    3. Set appropriate cap_score (usually 100, can be higher for exceptional performance)
    4. Generate 2-3 alternative formulas for user choice
    5. Provide clear explanation of how the formula works
    6. Ensure formula is mathematically sound and handles edge cases

    ## User Request
    Description: "{request.indicator_description}"

    ## Output Format (JSON only)
    {{
        "formula": "mathematical formula using available variables",
        "variables": {{
            "variable_name": {{"description": "description", "default_value": number}},
            "target_variable": {{"description": "description", "default_value": number}}
        }},
        "cap_score": number,
        "alternatives": ["alternative_formula_1", "alternative_formula_2"],
        "explanation": "clear explanation of how formula works and what it measures"
    }}

    Generate a professional, accurate formula that meets the user's requirements.
    """
        return prompt
    
    def _get_division_focus(self, division_code: str) -> str:
        """Get division focus description for AI context"""
        focus_map = {
            "IT": "Software development, code quality, and technical delivery",
            "TRAVEL_OPS": "Customer service, ticket processing, and satisfaction",
            "IT_OPS": "System reliability, incident management, and uptime",
            "FARE_FILING": "Regulatory compliance, filing accuracy, and timeliness",
            "FARE_LOADING": "Data loading speed, quality, and efficiency",
            "HR": "Employee management, attendance, and development",
            "SALES": "Revenue generation, deal closure, and client relationships"
        }
        return focus_map.get(division_code.upper(), "General operations and performance")
    
    def _call_ai_api(self, prompt: str) -> Dict[str, Any]:
        """
        Call Z.AI Coding Plan API for formula generation.

        Configurable via env:
            ZAI_TIMEOUT_SECONDS  (default 120) - per-request HTTP timeout
            ZAI_MAX_TOKENS       (default 2500) - max generated tokens
            ZAI_MAX_ATTEMPTS     (default 3)    - retries on timeout/429/5xx

        Args:
            prompt: AI prompt

        Returns:
            API response data
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timeout = float(os.getenv("ZAI_TIMEOUT_SECONDS", "120"))
        max_tokens = int(os.getenv("ZAI_MAX_TOKENS", "2500"))
        max_attempts = int(os.getenv("ZAI_MAX_ATTEMPTS", "3"))

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert KPI formula generator. Always respond with valid JSON only, no additional text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Low temperature for consistent results
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"}
        }

        last_error = "AI API request failed"
        for attempt in range(1, max_attempts + 1):
            try:
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(
                        self.base_url,
                        headers=headers,
                        json=data
                    )

                    if response.status_code == 200:
                        result = response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

                        try:
                            formula_data = json.loads(content)
                            return {"status": "success", "data": formula_data}
                        except json.JSONDecodeError:
                            logger.error(f"AI response not valid JSON: {content}")
                            return {"status": "error", "error": "AI response not valid JSON"}

                    elif response.status_code == 401:
                        logger.error("AI API authentication failed")
                        return {"status": "error", "error": "AI API authentication failed"}

                    elif response.status_code in (429, 500, 502, 503, 504):
                        last_error = f"AI API error: {response.status_code}"
                        logger.warning(f"{last_error} (attempt {attempt}/{max_attempts}), retrying...")
                        if attempt < max_attempts:
                            time.sleep(2 * attempt)
                            continue
                        return {"status": "error", "error": last_error}

                    else:
                        logger.error(f"AI API error: {response.status_code}")
                        return {"status": "error", "error": f"AI API error: {response.status_code}"}

            except httpx.TimeoutException:
                last_error = "AI API request timeout"
                logger.warning(f"{last_error} (attempt {attempt}/{max_attempts}), retrying...")
                if attempt < max_attempts:
                    time.sleep(2 * attempt)
                    continue
                return {"status": "error", "error": last_error}

            except Exception as e:
                last_error = str(e)
                logger.error(f"AI API call failed: {str(e)} (attempt {attempt}/{max_attempts})")
                if attempt < max_attempts:
                    time.sleep(2 * attempt)
                    continue
                return {"status": "error", "error": str(e)}

        return {"status": "error", "error": last_error}
    
    def _validate_formula(self, formula: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate generated formula against available variables
        
        Args:
            formula: Generated formula
            context: AI context
        
        Returns:
            Validation result
        """
        try:
            # Extract variables from formula
            variables_in_formula = self._extract_variables_from_formula(formula)
            available_var_names = [var["name"] for var in context["available_variables"]]
            
            # Check for undefined variables
            undefined_vars = [
                var for var in variables_in_formula 
                if var not in available_var_names
            ]
            
            # Test formula evaluation with sample data
            sample_context = {}
            for var in context["available_variables"]:
                var_name = var["name"]
                default_val = var.get("default_value")
                if default_val is not None:
                    sample_context[var_name] = default_val
                else:
                    # Provide default sample values
                    sample_context[var_name] = 10
            
            # Try to evaluate the formula
            try:
                from engine import evaluate_kpi_formula
                result = evaluate_kpi_formula(formula, sample_context, raise_on_error=True)
                eval_result = "success"
                eval_error = None
            except Exception as e:
                eval_result = "error"
                eval_error = str(e)
            
            return {
                "is_valid": len(undefined_vars) == 0 and eval_result == "success",
                "undefined_variables": undefined_vars,
                "evaluation_result": eval_result,
                "evaluation_error": eval_error,
                "warnings": [] if len(undefined_vars) == 0 else [f"Undefined variables: {', '.join(undefined_vars)}"]
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "error": str(e),
                "undefined_variables": [],
                "evaluation_result": "error",
                "evaluation_error": str(e),
                "warnings": []
            }
    
    def _extract_variables_from_formula(self, formula: str) -> List[str]:
        """
        Extract variable names from formula string
        
        Args:
            formula: Formula string
        
        Returns:
            List of variable names
        """
        import ast
        import re
        
        variables = set()
        
        # Remove function calls and operators
        cleaned_formula = re.sub(r'\b(min|max|abs|round|if)\s*\(', '', formula)
        cleaned_formula = re.sub(r'[+\-*/%<>=!&|^(),\s]', ' ', cleaned_formula)
        
        # Extract potential variable names
        tokens = cleaned_formula.split()
        for token in tokens:
            # Check if it's a valid variable name (letters, numbers, underscores)
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', token):
                # Exclude Python keywords and numbers
                if token not in ['and', 'or', 'not', 'in', 'is', 'True', 'False', 'None'] and not token.replace('.', '').isdigit():
                    variables.add(token)
        
        return list(variables)
    
    def _get_fallback_response(self, request: AIFormulaRequest, error_message: str = "AI service unavailable") -> AIFormulaResponse:
        """
        Generate fallback response when AI service is unavailable
        
        Args:
            request: AI formula generation request
            error_message: Error message
        
        Returns:
            Fallback response with suggestions
        """
        # Get division-specific examples
        example_prompts = get_division_example_prompts(request.division_code)
        
        return AIFormulaResponse(
            status="error",
            formula=None,
            variables={},
            cap_score=None,
            alternatives=[],
            explanation=f"AI formula generation is currently unavailable: {error_message}. Please try again later or use manual formula creation.",
            validation={
                "is_valid": False,
                "error": error_message,
                "warnings": ["AI service unavailable"]
            },
            error=error_message
        )

# Singleton instance for reuse
_ai_feature_sorer_instance = None

def get_ai_feature_sorer() -> AIFeatureScorer:
    """Get or create AI feature scorer instance"""
    global _ai_feature_sorer_instance
    if _ai_feature_sorer_instance is None:
        _ai_feature_sorer_instance = AIFeatureScorer()
    return _ai_feature_sorer_instance

def generate_formula_from_description(description: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to generate formula from description
    
    Args:
        description: Natural language description of indicator
        user_context: User context dictionary
    
    Returns:
        Generated formula response
    """
    scorer = get_ai_feature_sorer()
    
    request = AIFormulaRequest(
        user_id=user_context.get("user_id", ""),
        user_name=user_context.get("user_name", ""),
        user_role=user_context.get("user_role", "EMPLOYEE"),
        has_subordinates=user_context.get("has_subordinates", False),
        division_id=user_context.get("division_id", ""),
        division_name=user_context.get("division_name", ""),
        division_code=user_context.get("division_code", ""),
        group_id=user_context.get("group_id"),
        group_name=user_context.get("group_name"),
        creation_scope=user_context.get("creation_scope", "personal"),
        indicator_description=description
    )
    
    response = scorer.generate_formula(request)
    return response.dict()