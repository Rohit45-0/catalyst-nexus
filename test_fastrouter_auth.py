

import os
import requests
from dotenv import load_dotenv

# Force reload of .env
load_dotenv(override=True)

api_key = os.getenv("FASTROUTER_API_KEY")

print(f"--- API KEY DIAGNOSTICS ---")
if not api_key:
    print("❌ FASTROUTER_API_KEY is None or Empty!")
    exit(1)

print(f"Key Type: {type(api_key)}")
print(f"Key Length: {len(api_key)}")
print(f"Key Repr: {repr(api_key)}")
print(f"First 10 chars: {api_key[:10]}")
print(f"Last 5 chars: {api_key[-5:]}")

if '"' in api_key or "'" in api_key:
    print("⚠️  WARNING: Key contains quotes! This might be the issue.")
    
if " " in api_key:
    print("⚠️  WARNING: Key contains spaces! This might be the issue.")

print("\n--- CONNECTIVITY TEST ---")
url = "https://go.fastrouter.ai/api/v1/videos" # Endpoint for video generation
# Try a minimal valid payload to test auth (it might fail validation but pass auth)
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key.strip()}" # Strip just in case
}
payload = {
    "model": "bytedance/seedance-pro", 
    "length": 5,
    "prompt": "test"
}

try:
    print(f"POST {url}")
    # print headers masking key
    headers_masked = headers.copy()
    headers_masked["Authorization"] = f"Bearer {api_key[:5]}...{api_key[-5:]}"
    print(f"Headers: {headers_masked}")
    
    response = requests.post(url, json=payload, headers=headers)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Body: {response.text}")
    print(f"Response Headers: {response.headers}")

except Exception as e:
    print(f"Request Exception: {e}")

