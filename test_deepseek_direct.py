#!/usr/bin/env python3
"""Direct Deepseek API test with new OpenAI v1+ syntax."""
import os
os.environ["DEEPSEEK_API_KEY"] = "sk-be437db23efd4f248197cdb248beeaaf"

from openai import OpenAI
print(f"OpenAI client initialized")

# Configure for Deepseek
client = OpenAI(
    api_key="sk-be437db23efd4f248197cdb248beeaaf",
    base_url="https://api.deepseek.com"
)

print(f"API Base: https://api.deepseek.com")
print(f"Model: deepseek-chat")

try:
    print("\nCalling Deepseek ChatCompletion.create()...")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "Say ok"}],
        max_tokens=10,
        timeout=15
    )
    print(f"Success! Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
