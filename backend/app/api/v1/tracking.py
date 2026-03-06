"""
Tracking API
============

Endpoints for tracking system.
"""

from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from backend.app.db.base import get_db
from backend.app.db.models import ClickEvent, Campaign
from backend.app.services.tracking.geo_parser import GeoParser
from backend.app.services.tracking.link_generator import LinkGenerator
from backend.app.services.tracking.instagram.publisher import InstagramPublisher
from backend.app.core.security import get_current_user
from backend.app.db.models import User
from backend.app.db.schemas import CampaignCreate, CampaignResponse

router = APIRouter()


@router.post("/campaigns", response_model=CampaignResponse)
async def create_campaign(
    campaign: CampaignCreate,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)
):
    """Create a new campaign with tracking link."""
    # Generate campaign ID and link
    campaign_id = LinkGenerator.generate_campaign_id()
    tracking_link = LinkGenerator.generate_tracking_link(campaign_id)
    
    # Create campaign record
    db_campaign = Campaign(
        campaign_id=campaign_id,
        platform=campaign.platform,
        tracking_link=tracking_link,
        user_id=1  # Temporary test user ID
    )
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    
    return db_campaign


@router.post("/campaigns/{campaign_id}/publish-media")
async def publish_media_post(
    campaign_id: str,
    media_url: str,
    caption: str,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)
):
    """Publish a media post with tracking link."""
    # Get campaign
    campaign = db.query(Campaign).filter(
        Campaign.campaign_id == campaign_id
        # Campaign.user_id == current_user.id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Add tracking link to caption
    full_caption = f"{caption}\n\n{campaign.tracking_link}"
    
    # Publish to Instagram
    publisher = InstagramPublisher()
    post_id = publisher.publish_media_post(media_url, full_caption)
    
    if post_id:
        campaign.post_id = post_id
        campaign.publish_time = datetime.utcnow()
        db.commit()
        return {"post_id": post_id, "tracking_link": campaign.tracking_link}
    
    raise HTTPException(status_code=500, detail="Failed to publish post")


@router.get("/p/{campaign_id}")
async def track_click(
    campaign_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Track click on campaign link and redirect."""
    # Get client IP
    client_ip = request.client.host
    
    # Parse geo
    city, country = GeoParser.get_city_country(client_ip)
    
    if not city or not country:
        city, country = "Unknown", "Unknown"
    
    # Check if campaign exists
    campaign = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Store click event
    click_event = ClickEvent(
        campaign_id=campaign_id,
        city=city,
        country=country
    )
    db.add(click_event)
    db.commit()
    
    # Redirect to landing page (placeholder)
    return {"message": "Redirecting to content", "campaign": campaign_id}