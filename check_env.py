
import os
from dotenv import load_dotenv

load_dotenv()

fastrouter_key = os.getenv("FASTROUTER_API_KEY")
azure_key = os.getenv("AZURE_OPENAI_API_KEY")

print(f"FASTROUTER_API_KEY present: {bool(fastrouter_key)}")
if fastrouter_key:
    print(f"FASTROUTER_API_KEY length: {len(fastrouter_key)}")
    print(f"FASTROUTER_API_KEY start: {fastrouter_key[:5]}...")

print(f"AZURE_OPENAI_API_KEY present: {bool(azure_key)}")
if azure_key:
    print(f"AZURE_OPENAI_API_KEY length: {len(azure_key)}")
