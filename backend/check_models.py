import requests
import json
import os

api_key = os.getenv("FASTROUTER_API_KEY", "")
headers = {'Authorization': f'Bearer {api_key}'}
r = requests.get('https://go.fastrouter.ai/api/v1/models', headers=headers, timeout=30)
models = r.json().get('data', [])

print('VIDEO MODELS AND SUPPORTED PARAMETERS:')
print('='*70)
for m in models:
    modality = str(m.get('architecture', {}).get('modality', ''))
    if 'video' in modality.lower():
        print(f"Model: {m['id']}")
        print(f"  Params: {m.get('supported_parameters', [])}")
        print()
