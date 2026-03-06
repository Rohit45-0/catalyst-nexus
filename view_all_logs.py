"""
VIEW ALL TRACKING LOGS & ANALYTICS
==================================

This script shows you all the logs and analytics data in your database.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app.db.base import SessionLocal
from backend.app.db.models import Campaign, ClickEvent, InsightSnapshot
from sqlalchemy import func, desc

print("="*80)
print("📊 TRACKING LOGS & ANALYTICS VIEWER")
print("="*80)

db = SessionLocal()

try:
    # 1. ALL CAMPAIGNS
    print("\n" + "="*80)
    print("1️⃣ ALL CAMPAIGNS")
    print("="*80)
    
    campaigns = db.query(Campaign).order_by(desc(Campaign.created_at)).all()
    
    print(f"\nTotal Campaigns: {len(campaigns)}\n")
    
    for i, campaign in enumerate(campaigns, 1):
        print(f"Campaign {i}:")
        print(f"   Campaign ID: {campaign.campaign_id}")
        print(f"   Platform: {campaign.platform}")
        print(f"   Post ID: {campaign.post_id or 'Not published'}")
        print(f"   Tracking Link: {campaign.tracking_link}")
        print(f"   Created: {campaign.created_at}")
        print(f"   Published: {campaign.publish_time or 'Not published'}")
        
        # Count clicks for this campaign
        click_count = db.query(ClickEvent).filter(
            ClickEvent.campaign_id == campaign.campaign_id
        ).count()
        print(f"   Total Clicks: {click_count}")
        print()
    
    # 2. ALL CLICK EVENTS
    print("\n" + "="*80)
    print("2️⃣ ALL CLICK EVENTS (Recent 50)")
    print("="*80)
    
    clicks = db.query(ClickEvent).order_by(desc(ClickEvent.timestamp)).limit(50).all()
    
    print(f"\nTotal Click Events in Database: {db.query(ClickEvent).count()}")
    print(f"Showing most recent 50:\n")
    
    for i, click in enumerate(clicks, 1):
        print(f"{i:2}. {click.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | "
              f"Campaign: {click.campaign_id:30} | "
              f"{click.city:15} {click.country:10}")
    
    # 3. CLICK SUMMARY BY CAMPAIGN
    print("\n" + "="*80)
    print("3️⃣ CLICKS BY CAMPAIGN")
    print("="*80)
    
    click_summary = db.query(
        ClickEvent.campaign_id,
        func.count(ClickEvent.id).label('total_clicks'),
        func.count(func.distinct(ClickEvent.city)).label('unique_cities')
    ).group_by(ClickEvent.campaign_id).all()
    
    print()
    for summary in click_summary:
        print(f"Campaign: {summary.campaign_id}")
        print(f"   Total Clicks: {summary.total_clicks}")
        print(f"   Unique Cities: {summary.unique_cities}")
        print()
    
    # 4. CLICK SUMMARY BY CITY
    print("\n" + "="*80)
    print("4️⃣ TOP CITIES (All Campaigns)")
    print("="*80)
    
    city_summary = db.query(
        ClickEvent.city,
        ClickEvent.country,
        func.count(ClickEvent.id).label('total_clicks')
    ).group_by(ClickEvent.city, ClickEvent.country)\
     .order_by(desc('total_clicks')).limit(20).all()
    
    print()
    for i, city in enumerate(city_summary, 1):
        bar = "█" * min(city.total_clicks * 2, 40)
        print(f"{i:2}. {city.city:15} {city.country:10} {bar} {city.total_clicks} clicks")
    
    # 5. INSIGHT SNAPSHOTS
    print("\n" + "="*80)
    print("5️⃣ INSTAGRAM INSIGHT SNAPSHOTS")
    print("="*80)
    
    insights = db.query(InsightSnapshot).order_by(desc(InsightSnapshot.timestamp)).limit(20).all()
    
    print(f"\nTotal Insight Snapshots: {db.query(InsightSnapshot).count()}")
    
    if insights:
        print(f"Recent snapshots:\n")
        for i, insight in enumerate(insights, 1):
            print(f"{i}. {insight.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Campaign: {insight.campaign_id}")
            print(f"   City: {insight.city or 'N/A'}")
            print(f"   Reach: {insight.reach}, Engagement: {insight.engagement}")
            print()
    else:
        print("   No Instagram insights fetched yet.")
        print("   Run: POST /api/v1/analytics/campaigns/{campaign_id}/fetch-insights")
    
    # 6. MOST ACTIVE CAMPAIGN
    print("\n" + "="*80)
    print("6️⃣ MOST ACTIVE CAMPAIGN")
    print("="*80)
    
    if click_summary:
        most_active = max(click_summary, key=lambda x: x.total_clicks)
        
        print(f"\nMost Active Campaign: {most_active.campaign_id}")
        print(f"   Total Clicks: {most_active.total_clicks}")
        print(f"   Unique Cities: {most_active.unique_cities}")
        
        # Get click timeline for this campaign
        timeline = db.query(ClickEvent).filter(
            ClickEvent.campaign_id == most_active.campaign_id
        ).order_by(ClickEvent.timestamp).all()
        
        print(f"\n   Click Timeline:")
        for click in timeline[:10]:
            print(f"      {click.timestamp.strftime('%H:%M:%S')} - {click.city}, {click.country}")
    
    # 7. DATABASE STATS
    print("\n" + "="*80)
    print("7️⃣ DATABASE STATISTICS")
    print("="*80)
    
    print(f"\n   Total Campaigns: {db.query(Campaign).count()}")
    print(f"   Total Click Events: {db.query(ClickEvent).count()}")
    print(f"   Total Insight Snapshots: {db.query(InsightSnapshot).count()}")
    print(f"   Unique Cities Tracked: {db.query(func.count(func.distinct(ClickEvent.city))).scalar()}")
    print(f"   Unique Countries: {db.query(func.count(func.distinct(ClickEvent.country))).scalar()}")
    
finally:
    db.close()

print(f"\n{'='*80}")
print(f"📖 HOW TO ACCESS THIS DATA:")
print(f"{'='*80}")

print(f"\n1️⃣ VIA THIS SCRIPT:")
print(f"   python view_all_logs.py")

print(f"\n2️⃣ VIA API ENDPOINTS (once FastAPI running):")
print(f"   GET /api/v1/analytics/dashboard")
print(f"   GET /api/v1/analytics/campaigns/{{campaign_id}}/analytics")
print(f"   GET /api/v1/analytics/campaigns/{{campaign_id}}/timeline")
print(f"   GET /api/v1/analytics/campaigns/{{campaign_id}}/spread")

print(f"\n3️⃣ VIA DATABASE DIRECTLY:")
print(f"   Tables: campaigns, click_events, insight_snapshots")
print(f"   Tool: pgAdmin, DBeaver, or psql CLI")

print(f"\n4️⃣ VIA ANALYTICS SERVICE:")
print(f"   from backend.app.services.analytics_service import AnalyticsService")
print(f"   service = AnalyticsService(db)")
print(f"   analytics = service.get_campaign_analytics('campaign_id')")

print(f"\n{'='*80}")
print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*80}\n")
