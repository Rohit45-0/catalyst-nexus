"""
Analytics API Endpoints
=======================

Endpoints for viewing campaign analytics, insights, and dashboards.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.db.base import get_db
from backend.app.services.analytics_service import AnalyticsService
from backend.app.core.security import get_current_user
from backend.app.db.models import User

router = APIRouter()


@router.get("/campaigns/{campaign_id}/analytics")
async def get_campaign_analytics(
    campaign_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed analytics for a specific campaign.
    
    Returns:
    - Basic metrics (clicks, reach, engagement, shares, saves)
    - Geographic distribution
    - Spike detection results
    - Spread analysis with graph data
    """
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
    """
    Manually fetch latest insights from Instagram for a campaign.
    
    This fetches real-time data from Instagram API and stores it
    in the database for analysis.
    """
    service = AnalyticsService(db)
    result = await service.fetch_and_store_insights(campaign_id)
    return result


@router.post("/insights/fetch-all")
async def fetch_all_insights(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Fetch insights for all active campaigns.
    
    Optionally filter by user_id.
    """
    service = AnalyticsService(db)
    results = await service.fetch_all_campaign_insights(user_id=user_id)
    return {
        "total_campaigns": len(results),
        "successful": sum(1 for r in results if r.get("success")),
        "failed": sum(1 for r in results if not r.get("success")),
        "results": results
    }


@router.get("/dashboard")
async def get_analytics_dashboard(
    days: int = Query(default=7, ge=1, le=90),
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get analytics dashboard with aggregated metrics.
    
    Args:
        days: Number of days to analyze (1-90)
        user_id: Optional user filter
        
    Returns:
        - Aggregate metrics (total clicks, reach, engagement)
        - Top performing campaigns
        - All campaigns summary
    """
    service = AnalyticsService(db)
    dashboard = service.get_analytics_dashboard(days=days, user_id=user_id)
    return dashboard


@router.get("/campaigns/{campaign_id}/timeline")
async def get_click_timeline(
    campaign_id: str,
    db: Session = Depends(get_db)
):
    """
    Get timeline of click events for a campaign.
    
    Returns chronological list of clicks with timestamp,
    city, and country information.
    """
    service = AnalyticsService(db)
    timeline = service.get_click_timeline(campaign_id)
    return {
        "campaign_id": campaign_id,
        "total_clicks": len(timeline),
        "timeline": timeline
    }


@router.get("/campaigns/{campaign_id}/spread")
async def get_spread_analysis(
    campaign_id: str,
    db: Session = Depends(get_db)
):
    """
    Get geographic spread analysis for a campaign.
    
    Returns:
        - Active nodes (cities with engagement)
        - Spread edges (city-to-city propagation)
        - Trending and emerging cities
    """
    service = AnalyticsService(db)
    spread_data = service.spread_graph.analyze_spread(campaign_id)
    return spread_data


@router.get("/campaigns/{campaign_id}/spikes")
async def get_spike_detection(
    campaign_id: str,
    threshold: float = Query(default=1.5, ge=1.0, le=5.0),
    db: Session = Depends(get_db)
):
    """
    Detect engagement spikes in specific cities.
    
    Args:
        threshold: Growth multiplier to detect as spike (default 1.5x)
        
    Returns:
        List of cities with detected engagement spikes
    """
    service = AnalyticsService(db)
    spikes = service.spike_detector.detect_spikes(campaign_id, threshold=threshold)
    return {
        "campaign_id": campaign_id,
        "threshold": threshold,
        "spike_cities": spikes,
        "spike_count": len(spikes)
    }


@router.get("/health")
async def analytics_health():
    """Check if analytics service is healthy."""
    return {
        "status": "healthy",
        "service": "analytics",
        "features": [
            "campaign_analytics",
            "insights_fetching",
            "dashboard",
            "timeline",
            "spread_analysis",
            "spike_detection",
            "trending_reels_ingestion"
        ]
    }


@router.get("/competitor-content-intel")
async def get_competitor_content_intel(
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db)
    return service.get_competitor_content_intel(limit=limit)


@router.post("/trending-reels/ingest")
async def ingest_trending_reels(
    category: str,
    limit_per_hashtag: int = Query(default=20, ge=5, le=50),
    locale: str = Query(default="IN", min_length=2, max_length=5),
    db: Session = Depends(get_db)
):
    """
    Pull trending Instagram Reel/media metadata by category hashtags and
    store normalized training-ready features for GNN/analytics.
    """
    service = AnalyticsService(db)
    result = service.ingest_trending_reels_by_category(
        category=category,
        limit_per_hashtag=limit_per_hashtag,
        locale=locale,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result
