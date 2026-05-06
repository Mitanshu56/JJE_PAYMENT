"""
Test script for chatbot endpoints with the new DB-first routing
"""
import asyncio
import httpx
import json

BASE_URL = "http://127.0.0.1:8000"
FISCAL_YEAR = "FY-2025-2026"

# Mock authorization headers (update as needed for your auth scheme)
HEADERS = {
    "Authorization": "Bearer test_token",
    "Content-Type": "application/json"
}

async def test_index():
    """Test indexing endpoint"""
    print("\n" + "="*60)
    print("TEST: Index bills for fiscal year")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30) as client:
        payload = {
            "fiscal_year": FISCAL_YEAR
        }
        try:
            resp = await client.post(
                f"{BASE_URL}/api/chatbot/index",
                json=payload,
                headers=HEADERS
            )
            print(f"Status: {resp.status_code}")
            data = resp.json()
            print(json.dumps(data, indent=2))
            return resp.status_code == 200
        except Exception as e:
            print(f"ERROR: {e}")
            return False


async def test_chat(message: str, test_name: str = ""):
    """Test chat endpoint"""
    print("\n" + "="*60)
    print(f"TEST: Chat - {test_name}")
    print(f"Query: {message}")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30) as client:
        payload = {
            "message": message,
            "include_context": True
        }
        try:
            resp = await client.post(
                f"{BASE_URL}/api/chatbot/chat",
                json=payload,
                headers=HEADERS
            )
            print(f"Status: {resp.status_code}")
            data = resp.json()
            print(f"\nResponse: {data.get('response', 'N/A')}")
            if data.get('context_summary'):
                print(f"\nContext Summary: {json.dumps(data.get('context_summary'), indent=2)}")
            print(f"Tokens Used: {data.get('tokens_used', 'N/A')}")
            return resp.status_code == 200
        except Exception as e:
            print(f"ERROR: {e}")
            return False


async def run_tests():
    """Run all chatbot tests"""
    print("\n" + "="*70)
    print("CHATBOT ENDPOINT TESTS - DB-FIRST ROUTING")
    print("="*70)
    
    # Test 1: Index data
    print("\n[1/9] Indexing bills...")
    await test_index()
    
    # Wait for indexing to complete
    await asyncio.sleep(2)
    
    # Test 2: Global queries (should not require party name, use database)
    print("\n[2/9] Global query: month bill count")
    await test_chat(
        "how many number of bills are there in december month",
        "Month bill count (global, no party required)"
    )
    
    print("\n[3/9] Global query: pending bill count")
    await test_chat(
        "total number of pending bills",
        "Pending bill count (global)"
    )
    
    print("\n[4/9] Global query: pending bills list")
    await test_chat(
        "pending bills",
        "Pending bills list (first 10)"
    )
    
    print("\n[5/9] Global query: total pending amount")
    await test_chat(
        "total pending amount",
        "Total pending amount (global)"
    )
    
    # Test 6-8: Client-scoped queries (should require party name, use fuzzy matching)
    print("\n[6/9] Client-scoped query: pending amount for client")
    await test_chat(
        "pending amount for Enviro Control",
        "Pending amount for specific client (requires party name)"
    )
    
    print("\n[7/9] Client-scoped query: bill count for client")
    await test_chat(
        "how many bills of Enviro Control",
        "Bill count for specific client"
    )
    
    print("\n[8/9] Client-scoped query: payment history")
    await test_chat(
        "payment history of ABC Traders",
        "Payment history for specific client"
    )
    
    # Test 9: General RAG query (no database, use RAG)
    print("\n[9/9] General RAG query: explanation")
    await test_chat(
        "explain what pending bills mean",
        "General explanation (RAG allowed)"
    )
    
    print("\n" + "="*70)
    print("ALL TESTS COMPLETED")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(run_tests())
