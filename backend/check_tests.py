"""Quick script to check test video status."""
import requests
import json
import os

API_KEY = os.getenv("FASTROUTER_API_KEY", "")
BASE_URL = "https://go.fastrouter.ai/api/v1"

headers = {"Authorization": f"Bearer {API_KEY}"}

tests = [
    ("cml7x8i3a03w544hj0futcxce", "image_tail"),
    ("cml7xlast03vkuxe5crp2ebl3", "negative_prompt"),
    ("cml7xmfh703xb93ynkw99o3rr", "cfg_scale"),
    ("cml7xmoq2043q6d08555r9tcy", "camera_control")
]

print("=" * 60)
print("PARAMETER TEST RESULTS")
print("=" * 60)

for task_id, param in tests:
    try:
        r = requests.get(f"{BASE_URL}/videos/{task_id}", headers=headers, timeout=30)
        data = r.json()
        
        if "data" in data and "generations" in data["data"]:
            gen = data["data"]["generations"][0]
            status = gen.get("status", "unknown")
            url = gen.get("url", "")
            
            print(f"{param:20} | Status: {status:10}")
            if url:
                print(f"                     | URL: {url[:70]}...")
        else:
            print(f"{param:20} | Response: {str(data)[:60]}...")
    except Exception as e:
        print(f"{param:20} | Error: {e}")
    print("-" * 60)
