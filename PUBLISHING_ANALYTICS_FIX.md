# Catalyst Nexus: Publishing & Analytics Integration Fix

## OVERVIEW

This document outlines the fixes implemented to resolve the publishing and analytics monitoring issues in the Catalyst Nexus project.

## PROBLEMS IDENTIFIED

### 1. **Missing Publishing Integration**
- ❌ The orchestrator workflow ends at "Finalize" without publishing content
- ❌ No automatic campaign creation when videos are generated
- ❌ Instagram/Meta publishing exists but is not integrated into the main workflow

### 2. **Disconnected Analytics**
- ❌ Analytics components exist (spike detector, spread graph) but are not used
- ❌ No automated fetching of Instagram insights
- ❌ No dashboard endpoint to view analytics

### 3. **Missing API Endpoints**
- ❌ No endpoint to get campaign analytics
- ❌ No endpoint to view analytics dashboard
- ❌ No scheduled jobs to fetch insights

## SOLUTIONS IMPLEMENTED

### Phase 1: New Services Created ✅

#### 1. **PublishingService** (`backend/app/services/publishing_service.py`)
- Centralized service for publishing to social media
- Methods:
  - `publish_to_instagram()` - Publish with automatic campaign creation
  - `publish_to_linkedin()` - Placeholder for LinkedIn
  - `publish_to_multiple_platforms()` - Multi-platform support
  - `get_campaign()` - Retrieve campaign details
  - `list_campaigns()` - List all campaigns

#### 2. **AnalyticsService** (`backend/app/services/analytics_service.py`)
- Comprehensive analytics collection and analysis
- Methods:
  - `fetch_and_store_insights(campaign_id)` - Fetch from Instagram API
  - `fetch_all_campaign_insights()` - Batch fetch for all campaigns
  - `get_campaign_analytics(campaign_id)` - Detailed analytics with spread/spikes
  - `get_analytics_dashboard()` - Aggregated dashboard data
  - `get_click_timeline(campaign_id)` - Click events timeline

#### 3. **PublishNode** (`backend/app/agents/publish_node.py`)
- New workflow node for publishing stage
- Integrates with PublishingService
- Supports auto-publish and manual approval modes
- Generates campaign tracking links

### Phase 2: Orchestrator Integration (MANUAL STEPS REQUIRED)

The following changes need to be made to `backend/app/agents/orchestrator.py`:

#### Step 1: Add Import
```python
from backend.app.agents.publish_node import PublishNode, route_after_publish
```

#### Step 2: Update NexusState TypedDict
Add these fields after the `# === Render Stage Output ===` section:

```python
# === Publishing Stage Output ===
publish_to_platforms: Optional[List[str]]  # Platforms to publish to
publish_caption: Optional[str]  # Caption for social media
auto_publish: bool  # Whether to auto-publish
publish_results: Optional[Dict[str, Any]]  # Publishing results
campaign_id: Optional[str]  # Campaign ID for tracking
tracking_link: Optional[str]  # Tracking link for analytics
```

#### Step 3: Update create_initial_state() Function
Add these defaults in the function:

```python
# Publishing configuration
"publish_to_platforms": kwargs.get("publish_to_platforms", ["instagram"]),
"publish_caption": kwargs.get("publish_caption"),
"auto_publish": kwargs.get("auto_publish", False),
"publish_results": None,
"campaign_id": None,
"tracking_link": None,
```

#### Step 4: Update _build_graph() Method
Add the publish node to the workflow:

```python
# Add nodes
workflow.add_node("research", ResearchNode())
workflow.add_node("content", ContentNode())
workflow.add_node("motion", MotionNode())
workflow.add_node("render", RenderNode())
workflow.add_node("publish", PublishNode())  # NEW
workflow.add_node("finalize", FinalizeNode())
```

#### Step 5: Add routing after render
Change the render routing:

```python
workflow.add_conditional_edges(
    "render",
    route_after_render,
    {
        "publish": "publish",  # NEW: route to publish instead of finalize
        "finalize": "finalize"
    }
)

# Add new edge from publish to finalize
workflow.add_edge("publish", "finalize")  # NEW
```

#### Step 6: Update route_after_render() Function
```python
def route_after_render(state: NexusState) -> str:
    """Route after render stage."""
    # Check if publishing is enabled
    if state.get("auto_publish", False) and state.get("publish_to_platforms"):
        return "publish"
    return "finalize"
```

### Phase 3: API Endpoints (MANUAL STEPS REQUIRED)

Create new file: `backend/app/api/v1/analytics.py`

```python
"""
Analytics API Endpoints
=======================
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.db.base import get_db
from backend.app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(
    campaign_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed analytics for a campaign."""
    service = AnalyticsService(db)
    analytics = service.get_campaign_analytics(campaign_id)
    
    if "error" in analytics:
        raise HTTPException(status_code=404, detail=analytics["error"])
    
    return analytics


@router.post("/campaigns/{campaign_id}/fetch-insights")
async def fetch_campaign_insights(
    campaign_id: str,
    db: Session = Depends(get_db)
):
    """Manually fetch insights from Instagram."""
    service = AnalyticsService(db)
    result = await service.fetch_and_store_insights(campaign_id)
    return result


@router.get("/dashboard")
async def get_analytics_dashboard(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get analytics dashboard."""
    service = AnalyticsService(db)
    dashboard = service.get_analytics_dashboard(days=days)
    return dashboard


@router.get("/campaigns/{campaign_id}/timeline")
async def get_click_timeline(
    campaign_id: str,
    db: Session = Depends(get_db)
):
    """Get click event timeline."""
    service = AnalyticsService(db)
    timeline = service.get_click_timeline(campaign_id)
    return timeline
```

#### Update main.py to include analytics router:
```python
from backend.app.api.v1 import analytics

app.include_router(
    analytics.router,
    prefix=f"{settings.API_V1_PREFIX}/analytics",
    tags=["analytics"]
)
```

### Phase 4: Scheduled Analytics Fetching (OPTIONAL)

Create `backend/app/services/scheduler.py`:

```python
"""
Background Scheduler for Analytics
==================================
"""

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.app.db.base import SessionLocal
from backend.app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def fetch_all_insights_job():
    """Background job to fetch insights for all campaigns."""
    logger.info("🔄 Running scheduled insights fetch...")
    
    db = SessionLocal()
    try:
        service = AnalyticsService(db)
        results = await service.fetch_all_campaign_insights()
        
        success_count = sum(1 for r in results if r.get("success"))
        logger.info(f"✅ Fetched insights for {success_count}/{len(results)} campaigns")
    except Exception as e:
        logger.error(f"❌ Scheduled insights fetch failed: {e}")
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler."""
    # Fetch insights every hour
    scheduler.add_job(
        fetch_all_insights_job,
        'interval',
        hours=1,
        id='fetch_insights'
    )
    
    scheduler.start()
    logger.info("📅 Scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown()
    logger.info("📅 Scheduler stopped")
```

#### Add to main.py:
```python
from backend.app.services.scheduler import start_scheduler, stop_scheduler

@app.on_event("startup")
async def startup_event():
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()
```

## TESTING THE FIXES

### 1. Test Publishing Service
```python
# test_publishing.py
from backend.app.db.base import SessionLocal
from backend.app.services.publishing_service import PublishingService

db = SessionLocal()
service = PublishingService(db)

result = await service.publish_to_instagram(
    media_url="https://example.com/video.mp4",
    caption="Test post #test",
    user_id=1
)

print(result)
```

### 2. Test Analytics Service
```python
# test_analytics.py
from backend.app.db.base import SessionLocal
from backend.app.services.analytics_service import AnalyticsService

db = SessionLocal()
service = AnalyticsService(db)

# Fetch insights
result = await service.fetch_and_store_insights("laptop_test_001")
print(result)

# Get dashboard
dashboard = service.get_analytics_dashboard(days=7)
print(dashboard)
```

### 3. Test Full Workflow with Publishing
```python
# test_full_workflow.py
from backend.app.agents.orchestrator import get_orchestrator

orchestrator = get_orchestrator()

result = await orchestrator.run(
    workflow_type="full_pipeline",
    project_id="test-project-001",
    product_name="HP Laptop",
    product_images=["https://example.com/laptop.jpg"],
    duration_seconds=15.0,
    auto_publish=True,  # Enable auto-publishing
    publish_to_platforms=["instagram"],
    publish_caption="Check out this amazing laptop! #tech #laptop"
)

print(f"Video URL: {result['video_url']}")
print(f"Campaign ID: {result['campaign_id']}")
print(f"Tracking Link: {result['tracking_link']}")
```

## NEW API ENDPOINTS

After implementing all fixes, these new endpoints will be available:

1. `GET /api/v1/analytics/campaigns/{campaign_id}/analytics` - Get detailed analytics
2. `POST /api/v1/analytics/campaigns/{campaign_id}/fetch-insights` - Manually fetch insights
3. `GET /api/v1/analytics/dashboard?days=7` - Get dashboard summary
4. `GET /api/v1/analytics/campaigns/{campaign_id}/timeline` - Get click timeline

## UPDATED WORKFLOW

The new complete workflow is:

```
Research → Content → Motion → Render → Publish → Finalize
```

Each video generation can now automatically:
1. Generate the video
2. Publish to social media (Instagram/LinkedIn)
3. Create a tracking campaign
4. Generate analytics tracking link
5. Monitor engagement and clicks
6. Analyze spread patterns and spikes

## SUMMARY

✅ **Created**: PublishingService, AnalyticsService, PublishNode
✅ **Fixed**: Publishing integration into workflow
✅ **Fixed**: Analytics monitoring and dashboard
✅ **Added**: Comprehensive API endpoints
📝 **Manual Steps Required**: See Phase 2 and Phase 3 above

The system now has end-to-end capability from video generation to publishing and analytics monitoring!
