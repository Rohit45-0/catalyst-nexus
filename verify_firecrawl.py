
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.app.core.config import settings
# Manually import to avoid complex dependencies if possible, or just standard import
try:
    from firecrawl import FirecrawlApp
except ImportError:
    print("CRITICAL: firecrawl module not found!", flush=True)
    sys.exit(1)

def test_firecrawl():
    key = settings.FIRECRAWL_API_KEY
    if not key:
        print("FAIL: No FIRECRAWL_API_KEY in settings", flush=True)
        return

    masked = key[:4] + "..." + key[-4:]
    print(f"Testing FirecrawlApp with key: {masked}", flush=True)
    
    app = FirecrawlApp(api_key=key)
    try:
        print("Sending search request...", flush=True)
        # Search for something simple
        results = app.search("Nike marketing", params={"limit": 1})
        print(f"Raw result type: {type(results)}", flush=True)
        print(f"Raw result: {results}", flush=True)
        
        if results and (isinstance(results, list) or results.get('data')):
            print("SUCCESS: Firecrawl returned data.", flush=True)
        else:
            print("FAIL: Firecrawl returned empty result.", flush=True)
            
    except Exception as e:
        print(f"EXCEPTION: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_firecrawl()
