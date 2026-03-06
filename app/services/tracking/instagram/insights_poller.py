"""
Insights Poller
================

Polls Instagram for insights and stores snapshots.
"""

import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.db.models import InsightSnapshot, Campaign
from backend.app.services.tracking.instagram.publisher import InstagramPublisher


class InsightsPoller:
    """Polls Instagram insights periodically."""
    
    def __init__(self, db: Session):
        self.db = db
        self.publisher = InstagramPublisher()
    
    async def poll_all_campaigns(self):
        """Poll insights for all active campaigns."""
        campaigns = self.db.query(Campaign).filter(Campaign.post_id.isnot(None)).all()
        
        for campaign in campaigns:
            insights = self.publisher.get_post_insights(campaign.post_id)
            
            # Parse insights (simplified)
            reach = insights.get('reach', {}).get('values', [{}])[0].get('value')
            impressions = insights.get('impressions', {}).get('values', [{}])[0].get('value')
            
            snapshot = InsightSnapshot(
                campaign_id=campaign.campaign_id,
                reach=reach,
                impressions=impressions
            )
            self.db.add(snapshot)
        
        self.db.commit()
    
    async def start_polling(self, interval_minutes: int = 15):
        """Start periodic polling."""
        while True:
            await self.poll_all_campaigns()
            await asyncio.sleep(interval_minutes * 60)
