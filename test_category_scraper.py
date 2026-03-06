
import asyncio
import json
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app.services.market_intel_service import MarketIntelService

def log_file(msg):
    with open("category_test.log", "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")
        f.flush()
    print(msg, flush=True)

async def run_test():
    log_file("="*60)
    log_file("🚀 CATEGORY-WISE NICHE SCRAPER TEST")
    log_file("="*60)
    
    try:
        service = MarketIntelService()
        log_file("✅ MarketIntelService initialized")
        
        # Target Category
        category = "Tech" 
        log_file(f"\n🔍 Analyzing Niche: {category}...")
        
        # This will:
        # 1. Map 'Tech' to #techreview, #gadgetlife
        # 2. Scrape top posts for these hashtags (Instaloader)
        # 3. Pull comments for top posts
        # 4. Use LLM to find the 'Opportunity Gap' in the whole category
        result = await service.analyze_category(category)
        
        if "error" in result:
             log_file(f"❌ Error in result: {result['error']}")
             return

        log_file(f"\n✅ Analysis for {category} Complete!")
        log_file(f"\n📈 Trending Hashtags: {result.get('hashtag_trends')}")
        
        analysis = result.get("analysis", {})
        log_file("\n🎯 OPPORTUNITY GAP FOUND:")
        log_file(f"   {analysis.get('opportunity_gap', 'N/A')}")
        
        log_file("\n❓ Top Questions Audience is Asking:")
        for q in analysis.get("top_questions", []):
            log_file(f"   - {q}")
            
        log_file("\n💡 Suggested Viral Hooks:")
        for h in analysis.get("viral_hooks", []):
            log_file(f"   - {h}")
            
        # Save to file
        with open(f"market_intel_{category.lower()}.json", "w") as f:
            json.dump(result, f, indent=2)
        log_file(f"\n💾 Full report saved to market_intel_{category.lower()}.json")
        
    except Exception as e:
        log_file(f"\n❌ Test Failed: {e}")
        import traceback
        log_file(traceback.format_exc())

if __name__ == "__main__":
    if os.path.exists("category_test.log"):
        os.remove("category_test.log")
    asyncio.run(run_test())
