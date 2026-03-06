
import os
import sys

with open("import_debug.log", "w") as f:
    f.write("Import Debugging Started...\n")
    f.flush()
    
    try:
        f.write("Current path: " + str(sys.path) + "\n")
        sys.path.insert(0, ".")
        f.flush()
        
        f.write("Importing pydantic...\n")
        import pydantic
        f.write("✅ pydantic version: " + pydantic.__version__ + "\n")
        f.flush()
        
        f.write("Importing instaloader...\n")
        import instaloader
        f.write("✅ instaloader version: " + instaloader.__version__ + "\n")
        f.flush()
        
        f.write("Importing backend.app.core.config...\n")
        from backend.app.core.config import settings
        f.write("✅ Settings imported. Database URL set: " + str(bool(settings.DATABASE_URL)) + "\n")
        f.flush()

        f.write("Importing backend.app.services.social_scraper...\n")
        from backend.app.services.social_scraper import SocialScraperService
        f.write("✅ SocialScraperService imported.\n")
        f.flush()

        f.write("Importing backend.app.services.market_intel_service...\n")
        from backend.app.services.market_intel_service import MarketIntelService
        f.write("✅ MarketIntelService imported.\n")
        f.flush()

    except Exception as e:
        f.write(f"❌ FAILED: {str(e)}\n")
        import traceback
        f.write(traceback.format_exc())
        f.flush()
