#!/usr/bin/env python3
"""Test LLM endpoint with detailed debugging"""
import urllib.request
import json
import traceback

try:
    print("Testing OpenRouter connection...")
    url = "http://127.0.0.1:8000/api/chatbot/llm/test/public"
    print(f"URL: {url}")
    
    req = urllib.request.Request(url)
    req.add_header('Accept', 'application/json')
    
    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode())
        print("Response:", json.dumps(result, indent=2))
        
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}")
    print("Headers:", dict(e.headers))
    body = e.read().decode()
    print("Body:", body[:800])
    
except urllib.error.URLError as e:
    print(f"URL Error: {type(e.reason).__name__}: {e.reason}")
    traceback.print_exc()
    
except Exception as e:
    print(f"Error: {type(e).__name__}")
    traceback.print_exc()
