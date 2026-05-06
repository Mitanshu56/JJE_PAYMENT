#!/usr/bin/env python3
"""Quick test script for Deepseek chatbot endpoint."""
import json
import urllib.request
import urllib.error

url = "http://127.0.0.1:8000/api/chatbot/llm/test/public"

try:
    print(f"Testing endpoint: {url}")
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as response:
        print(f"Status Code: {response.status}")
        data = response.read()
        result = json.loads(data)
    print(f"Response:\n{json.dumps(result, indent=2)}")
except Exception as e:
    print(f"Error: {e}")
