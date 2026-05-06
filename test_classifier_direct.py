"""
Direct unit tests for chatbot routing logic
Tests the classifier, party extraction, and database handlers without HTTP auth
"""
import asyncio
from app.routes.chatbot_routes import (
    classify_query_intent,
    _extract_party_name,
    normalize_party_name,
)

def test_classifier_global_queries():
    """Test that global queries don't require party names"""
    print("\n" + "="*70)
    print("TEST: Classifier - Global Queries")
    print("="*70)
    
    test_cases = [
        (
            "how many number of bills are there in december month",
            "month_bill_count",
            False,  # requires_party_name
        ),
        (
            "total number of pending bills",
            "pending_bill_count",
            False,
        ),
        (
            "pending bills",
            "pending_bill_list",
            False,
        ),
        (
            "total pending amount",
            "total_pending_amount",
            False,
        ),
        (
            "how many invoices in january",
            "month_bill_count",
            False,
        ),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_intent, expected_requires_party in test_cases:
        result = classify_query_intent(query)
        intent = result.get("intent")
        requires_party = result.get("requires_party_name")
        
        intent_match = intent == expected_intent
        party_match = requires_party == expected_requires_party
        
        status = "✓ PASS" if (intent_match and party_match) else "✗ FAIL"
        
        print(f"\n{status}")
        print(f"  Query: {query}")
        print(f"  Expected intent: {expected_intent}, Got: {intent} {'✓' if intent_match else '✗'}")
        print(f"  Expected requires_party: {expected_requires_party}, Got: {requires_party} {'✓' if party_match else '✗'}")
        print(f"  Full result: {result}")
        
        if intent_match and party_match:
            passed += 1
        else:
            failed += 1
    
    print(f"\n\nGlobal Queries: {passed} passed, {failed} failed")
    return failed == 0


def test_classifier_client_queries():
    """Test that client-scoped queries require party names"""
    print("\n" + "="*70)
    print("TEST: Classifier - Client-Scoped Queries")
    print("="*70)
    
    test_cases = [
        (
            "pending amount for Enviro Control",
            "client_pending_amount",
            True,  # requires_party_name
        ),
        (
            "how many bills of Enviro Control",
            "client_invoice_count",
            True,
        ),
        (
            "payment history of ABC Traders",
            "payment_history",
            True,
        ),
        (
            "outstanding balance for XYZ Pvt Ltd",
            "client_pending_amount",
            True,
        ),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_intent, expected_requires_party in test_cases:
        result = classify_query_intent(query)
        intent = result.get("intent")
        requires_party = result.get("requires_party_name")
        
        intent_match = intent == expected_intent
        party_match = requires_party == expected_requires_party
        
        status = "✓ PASS" if (intent_match and party_match) else "✗ FAIL"
        
        print(f"\n{status}")
        print(f"  Query: {query}")
        print(f"  Expected intent: {expected_intent}, Got: {intent} {'✓' if intent_match else '✗'}")
        print(f"  Expected requires_party: {expected_requires_party}, Got: {requires_party} {'✓' if party_match else '✗'}")
        print(f"  Full result: {result}")
        
        if intent_match and party_match:
            passed += 1
        else:
            failed += 1
    
    print(f"\n\nClient-Scoped Queries: {passed} passed, {failed} failed")
    return failed == 0


def test_party_extraction():
    """Test party name extraction"""
    print("\n" + "="*70)
    print("TEST: Party Name Extraction")
    print("="*70)
    
    test_cases = [
        (
            "pending amount for Enviro Control Private LTD",
            "Enviro Control Private LTD",
        ),
        (
            "how many bills of client Enviro Control",
            "Enviro Control",
        ),
        (
            "payment history of ABC Traders",
            "ABC Traders",
        ),
        (
            "outstanding balance for XYZ Pvt Ltd",
            "XYZ Pvt Ltd",
        ),
        (
            "show invoices for client name ABC Company",
            "ABC Company",
        ),
        (
            "total number of pending bills",  # Global query, no party
            None,
        ),
        (
            "pending bills",  # Global query, no party
            None,
        ),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_party in test_cases:
        result = _extract_party_name(query)
        match = result == expected_party
        
        status = "✓ PASS" if match else "✗ FAIL"
        
        print(f"\n{status}")
        print(f"  Query: {query}")
        print(f"  Expected: {expected_party}, Got: {result}")
        
        if match:
            passed += 1
        else:
            failed += 1
    
    print(f"\n\nParty Extraction: {passed} passed, {failed} failed")
    return failed == 0


def test_party_normalization():
    """Test party name normalization"""
    print("\n" + "="*70)
    print("TEST: Party Name Normalization")
    print("="*70)
    
    test_cases = [
        ("Enviro Control Private LTD", "enviro control"),
        ("ABC Traders, Inc.", "abc traders"),
        ("XYZ Pvt. Ltd.", "xyz"),
        ("  Company Name  ", "company name"),
        ("ABC LLP", "abc"),
    ]
    
    passed = 0
    failed = 0
    
    for input_name, expected_normalized in test_cases:
        result = normalize_party_name(input_name)
        match = result == expected_normalized
        
        status = "✓ PASS" if match else "✗ FAIL"
        
        print(f"\n{status}")
        print(f"  Input: {input_name}")
        print(f"  Expected: {expected_normalized}")
        print(f"  Got: {result}")
        
        if match:
            passed += 1
        else:
            failed += 1
    
    print(f"\n\nParty Normalization: {passed} passed, {failed} failed")
    return failed == 0


def test_classifier_databases_only_queries():
    """Test that DB-only queries have requires_database=True"""
    print("\n" + "="*70)
    print("TEST: Classifier - Database-Only Queries")
    print("="*70)
    
    test_cases = [
        "total number of pending bills",
        "pending bills",
        "how many invoices this month",
        "payment history of ABC",
        "total pending amount",
        "bills in December",
    ]
    
    passed = 0
    failed = 0
    
    for query in test_cases:
        result = classify_query_intent(query)
        requires_db = result.get("requires_database")
        is_exact_numeric = result.get("requires_exact_numeric_answer")
        
        # Most financial queries should require database
        should_require_db = any(
            word in query.lower()
            for word in [
                "pending",
                "bill",
                "invoice",
                "payment",
                "total",
                "how many",
                "count",
            ]
        )
        
        match = requires_db == should_require_db
        
        status = "✓ PASS" if match else "✗ FAIL"
        
        print(f"\n{status}")
        print(f"  Query: {query}")
        print(f"  Expected requires_database: {should_require_db}, Got: {requires_db} {'✓' if match else '✗'}")
        print(f"  Intent: {result.get('intent')}, Exact Numeric: {is_exact_numeric}")
        
        if match:
            passed += 1
        else:
            failed += 1
    
    print(f"\n\nDatabase-Only Queries: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("CHATBOT ROUTING UNIT TESTS")
    print("="*70)
    
    all_passed = True
    
    # Run all tests
    all_passed = test_classifier_global_queries() and all_passed
    all_passed = test_classifier_client_queries() and all_passed
    all_passed = test_party_extraction() and all_passed
    all_passed = test_party_normalization() and all_passed
    all_passed = test_classifier_databases_only_queries() and all_passed
    
    print("\n" + "="*70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
