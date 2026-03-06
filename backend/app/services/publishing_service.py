"""
Publishing Service
==================

Handles publishing to social media platforms and campaign creation.
"""

from typing import Optional, Dict, List
from datetime import datetime
import logging
from sqlalchemy.orm import Session
from backend.app.db.models import Campaign, User
from backend.app.services.tracking.instagram.publisher import InstagramPublisher
from backend.app.services.tracking.link_generator import LinkGenerator

logger = logging.getLogger(__name__)


class PublishingService:
    """Service for publishing content to social media platforms."""
    
    def __init__(self, db: Session):
        self.db = db
        self.instagram_publisher = InstagramPublisher()
    
    async def publish_to_instagram(
        self,
        media_url: str,
        caption: str,
        campaign_id: Optional[str] = None,
        user_id: Optional[int] = None,
        add_tracking_link: bool = True
    ) -> Dict:
        """
        Publish media to Instagram with optional tracking.
        
        Args:
            media_url: URL of the media to publish
            caption: Caption for the post
            campaign_id: Optional campaign ID (will be generated if not provided)
            user_id: User ID for tracking
            add_tracking_link: Whether to add tracking link to caption
            
        Returns:
            Dictionary with post_id, campaign_id, and tracking_link
        """
        try:
            # Create or get campaign
            if not campaign_id:
                campaign_id = LinkGenerator.generate_campaign_id()
            
            tracking_link = LinkGenerator.generate_tracking_link(campaign_id)
            
            # Add tracking link to caption if requested
            final_caption = caption
            if add_tracking_link:
                final_caption = f"{caption}\n\n{tracking_link}"
            
            # Publish to Instagram
            post_id = self.instagram_publisher.publish_media_post(
                media_url=media_url,
                caption=final_caption
            )
            
            if not post_id:
                raise Exception("Failed to publish to Instagram")
            
            # Create campaign record
            campaign = Campaign(
                campaign_id=campaign_id,
                platform="instagram",
                post_id=post_id,
                publish_time=datetime.utcnow(),
                tracking_link=tracking_link,
                user_id=user_id or 1  # Default test user
            )
            self.db.add(campaign)
            self.db.commit()
            self.db.refresh(campaign)
            
            logger.info(f"✅ Published to Instagram: post_id={post_id}, campaign_id={campaign_id}")
            
            return {
                "success": True,
                "post_id": post_id,
                "campaign_id": campaign_id,
                "tracking_link": tracking_link,
                "platform": "instagram"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to publish to Instagram: {str(e)}")
            raise e
    
    async def publish_to_linkedin(
        self,
        media_url: str,
        caption: str,
        campaign_id: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict:
        """
        Publish media to LinkedIn.
        
        TODO: Implement LinkedIn publishing similar to Instagram
        """
        raise NotImplementedError("LinkedIn publishing not yet implemented")
    
    async def publish_to_multiple_platforms(
        self,
        media_url: str,
        captions: Dict[str, str],  # Platform-specific captions
        platforms: List[str],
        user_id: Optional[int] = None
    ) -> Dict[str, Dict]:
        """
        Publish to multiple platforms at once.
        
        Args:
            media_url: URL of the media to publish
            captions: Dictionary mapping platform names to captions
            platforms: List of platforms to publish to
            user_id: User ID for tracking
            
        Returns:
            Dictionary mapping platform names to publish results
        """
        results = {}
        
        for platform in platforms:
            caption = captions.get(platform, captions.get("default", ""))
            
            try:
                if platform.lower() == "instagram":
                    result = await self.publish_to_instagram(
                        media_url=media_url,
                        caption=caption,
                        user_id=user_id
                    )
                    results[platform] = result
                elif platform.lower() == "linkedin":
                    result = await self.publish_to_linkedin(
                        media_url=media_url,
                        caption=caption,
                        user_id=user_id
                    )
                    results[platform] = result
                else:
                    results[platform] = {
                        "success": False,
                        "error": f"Platform {platform} not supported"
                    }
            except Exception as e:
                results[platform] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by ID."""
        return self.db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id
        ).first()
    
    def list_campaigns(self, user_id: Optional[int] = None, limit: int = 50) -> List[Campaign]:
        """List campaigns, optionally filtered by user."""
        query = self.db.query(Campaign)
        
        if user_id:
            query = query.filter(Campaign.user_id == user_id)
        
        return query.order_by(Campaign.created_at.desc()).limit(limit).all()
