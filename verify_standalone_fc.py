
import sys
import os


# Standalone verification script logging to file
LOG_FILE = "fc_verify.log"

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")
    # Also attempt print just in case
    print(msg, flush=True)

# Clear log
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("Starting Firecrawl Verification...\n")

try:
    from firecrawl import FirecrawlApp
    log("Imported FirecrawlApp successfully.")
except ImportError as e:
    log(f"FAILED to import firecrawl: {e}")
    sys.exit(1)

def run():
    # Hardcoded key from .env for verification purposes only
    api_key = "fc-d4cd11d8942d42869bcaa51166fce7f0"
    
    log(f"Initializing FirecrawlApp with key ending in ...{api_key[-4:]}")
    app = FirecrawlApp(api_key=api_key)
    
    import inspect
    log(f"Signature of app.search: {inspect.signature(app.search)}")
    
    try:
        log("Searching via Firecrawl API (attempting correct args)...")
        # Correct usage for v1
        response = app.search("test query", limit=1)
        
        log("--- RAW RESPONSE START ---")
        log(response)
        log("--- RAW RESPONSE END ---")
            
    except Exception as e:
        log(f"VERDICT: Firecrawl FAILED with Exception: {type(e).__name__}: {e}")
        import traceback
        with open(LOG_FILE, "a") as f:
            traceback.print_exc(file=f)

if __name__ == "__main__":
    run()
