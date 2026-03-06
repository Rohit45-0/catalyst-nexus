
import asyncio
import logging
from backend.app.services.market_intel_service import MarketIntelService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_firecrawl_integration():
    service = MarketIntelService()
    print("Testing Firecrawl via analyze_category_trends...")
    try:
        # Simulate the call that failed
        result = await service.analyze_category_trends(
            category="nike shoes",
            platform="youtube", # Logic switches to 'heuristic' then Firecrawl if youtube fails/missing
            region_code="IN",
            max_results=5
        )
        print("Success!")
        print(result)
    except Exception as e:
        print(f"Error caught: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_firecrawl_integration())
