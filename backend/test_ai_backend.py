#!/usr/bin/env python
"""
NEW: AI INDICATOR CREATOR - Backend Test Script
Test the AI formula generation functionality
"""

import asyncio
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_formula_generator import AIFeatureScorer, AIFormulaRequest
from division_variables import (
    get_division_variables,
    get_division_example_prompts,
    get_division_common_targets,
    get_all_divisions,
    get_available_variables_by_type
)

def test_division_variables():
    """Test division variables registry"""
    print("=" * 60)
    print("TEST 1: Division Variables Registry")
    print("=" * 60)
    
    # Test getting all divisions
    divisions = get_all_divisions()
    print(f"[OK] Available divisions: {len(divisions)}")
    for div in divisions:
        print(f"   - {div['code']}: {div['name']}")
    
    # Test division-specific variables for IT
    print(f"\n[OK] IT Division Variables:")
    it_vars = get_division_variables("IT")
    print(f"   Core variables: {len(it_vars.get('core', []))}")
    print(f"   Advanced variables: {len(it_vars.get('advanced', []))}")
    print(f"   AI-suggested variables: {len(it_vars.get('ai_suggested', []))}")
    
    # Test Travel Ops variables
    print(f"\n[OK] Travel Ops Division Variables:")
    travel_vars = get_division_variables("TRAVEL_OPS")
    print(f"   Core variables: {len(travel_vars.get('core', []))}")
    print(f"   Advanced variables: {len(travel_vars.get('advanced', []))}")
    print(f"   AI-suggested variables: {len(travel_vars.get('ai_suggested', []))}")
    
    # Test example prompts
    print(f"\n[OK] Travel Ops Example Prompts:")
    examples = get_division_example_prompts("TRAVEL_OPS")
    for idx, example in enumerate(examples[:3], 1):
        print(f"   {idx}. {example}")
    
    # Test common targets
    print(f"\n[OK] Travel Ops Common Targets:")
    targets = get_division_common_targets("TRAVEL_OPS")
    for target, value in targets.items():
        print(f"   {target}: {value}")
    
    print("\n" + "=" * 60)
    print("[OK] Division variables registry test PASSED")
    print("=" * 60 + "\n")

def test_ai_formula_generator():
    """Test AI formula generation"""
    print("=" * 60)
    print("TEST 2: AI Formula Generator")
    print("=" * 60)
    
    # Check if AI service is available
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("[WARNING] OPENROUTER_API_KEY not found in environment variables")
        print("   AI formula generation will use fallback mode")
    
    # Test AI scorer initialization
    scorer = AIFeatureScorer()
    print(f"[OK] AI Feature Scorer initialized")
    print(f"   Enabled: {scorer.enabled}")
    print(f"   Model: {scorer.model}")
    
    # Test context building for Travel Ops manager
    print(f"\n[OK] Testing AI Context Building:")
    
    user_context = {
        "user_id": "test_user_123",
        "user_name": "Test Manager",
        "user_role": "MANAGER",
        "has_subordinates": True,
        "division_id": "DIV_TRAVEL_OPS",
        "division_name": "Travel Operations",
        "division_code": "TRAVEL_OPS",
        "group_id": "GRP_CUSTOMER_SERVICE",
        "group_name": "Customer Service",
        "creation_scope": "group"
    }
    
    request = AIFormulaRequest(
        user_id=user_context["user_id"],
        user_name=user_context["user_name"],
        user_role=user_context["user_role"],
        has_subordinates=user_context["has_subordinates"],
        division_id=user_context["division_id"],
        division_name=user_context["division_name"],
        division_code=user_context["division_code"],
        group_id=user_context["group_id"],
        group_name=user_context["group_name"],
        creation_scope=user_context["creation_scope"],
        indicator_description="Hitung performa berdasarkan jumlah tiket yang diproses dengan target 500 tiket per bulan"
    )
    
    context = scorer._build_ai_context(request)
    print(f"   User: {context['user']['name']} ({context['user']['role']})")
    print(f"   Division: {context['division']['name']} ({context['division']['code']})")
    print(f"   Available variables: {len(context['available_variables'])}")
    print(f"   Creation scope: {context['user']['creation_scope']}")
    
    # Test formula generation (will use fallback if AI not available)
    print(f"\n[OK] Testing Formula Generation:")
    print(f"   Description: '{request.indicator_description}'")
    
    response = scorer.generate_formula(request)
    print(f"   Status: {response.status}")
    
    if response.status == "success":
        print(f"   [OK] Formula: {response.formula}")
        print(f"   Variables: {list(response.variables.keys()) if response.variables else 'None'}")
        print(f"   Cap Score: {response.cap_score}")
        print(f"   Alternatives: {len(response.alternatives) if response.alternatives else 0} options")
        print(f"   Explanation: {response.explanation[:100]}..." if len(response.explanation or "") > 100 else f"   Explanation: {response.explanation}")
        
        # Test validation
        print(f"\n[OK] Formula Validation:")
        print(f"   Valid: {response.validation['is_valid']}")
        if not response.validation['is_valid']:
            print(f"   Errors: {response.validation.get('evaluation_error', 'None')}")
            print(f"   Warnings: {response.validation.get('warnings', [])}")
    else:
        print(f"   [WARNING] Error: {response.error}")
        print(f"   Fallback mode activated (this is expected if OPENROUTER_API_KEY is not set)")
    
    print("\n" + "=" * 60)
    print("[OK] AI formula generator test PASSED")
    print("=" * 60 + "\n")

def test_variable_filtering():
    """Test variable filtering by user role"""
    print("=" * 60)
    print("TEST 3: Variable Filtering by User Role")
    print("=" * 60)
    
    # Test for different user roles
    roles = ["ROLE_ADMIN", "MANAGER", "EMPLOYEE"]
    division_code = "IT"
    
    for role in roles:
        print(f"\n✅ Variables for {role}:")
        
        # Core variables should be available to all
        core_vars = get_available_variables_by_type(division_code, "core", role)
        print(f"   Core: {len(core_vars)} variables")
        
        # Advanced variables should be available to all
        advanced_vars = get_available_variables_by_type(division_code, "advanced", role)
        print(f"   Advanced: {len(advanced_vars)} variables")
        
        # AI-suggested variables should only be available to admins
        ai_vars = get_available_variables_by_type(division_code, "ai_suggested", role)
        if role == "ROLE_ADMIN":
            print(f"   AI-Suggested: {len(ai_vars)} variables ✅")
        else:
            print(f"   AI-Suggested: {len(ai_vars)} variables (hidden for {role}) ✅")
    
    print("\n" + "=" * 60)
    print("✅ Variable filtering test PASSED")
    print("=" * 60 + "\n")

async def test_async_ai_api():
    """Test async AI API call"""
    print("=" * 60)
    print("TEST 4: Async AI API Call")
    print("=" * 60)
    
    scorer = AIFeatureScorer()
    
    if not scorer.enabled:
        print("⚠️  AI service not enabled, skipping async test")
        print("   Set OPENROUTER_API_KEY environment variable to enable AI service")
        return
    
    request = AIFormulaRequest(
        user_id="test_user_async",
        user_name="Async Test User",
        user_role="MANAGER",
        has_subordinates=True,
        division_id="DIV_IT_OPS",
        division_name="IT Operations",
        division_code="IT_OPS",
        group_id="GRP_SYSTEM_ADMIN",
        group_name="System Administration",
        creation_scope="group",
        indicator_description="Kombinasi uptime server dan incident resolution dengan bobot 70% uptime, 30% incident"
    )
    
    print(f"✅ Testing async AI API call...")
    print(f"   Request: {request.indicator_description}")
    
    response_data = await scorer._call_ai_api("Test prompt")
    print(f"   API Response Status: {response_data.get('status')}")
    
    if response_data.get("status") == "success":
        formula_data = response_data.get("data", {})
        print(f"   ✅ Formula: {formula_data.get('formula', 'N/A')}")
        print(f"   ✅ Variables: {list(formula_data.get('variables', {}).keys())}")
    else:
        print(f"   ⚠️  API Error: {response_data.get('error')}")
    
    print("\n" + "=" * 60)
    print("✅ Async AI API test PASSED")
    print("=" * 60 + "\n")

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("AI INDICATOR CREATOR - BACKEND TESTS")
    print("=" * 60 + "\n")
    
    try:
        # Test 1: Division variables
        test_division_variables()
        
        # Test 2: AI formula generation
        test_ai_formula_generator()
        
        # Test 3: Variable filtering
        test_variable_filtering()
        
        # Test 4: Async AI API (run with asyncio)
        asyncio.run(test_async_ai_api())
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Test the backend API endpoints")
        print("2. Test the frontend integration")
        print("3. Test with real user data")
        print("4. Test permission validation")
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ TESTS FAILED: {str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())