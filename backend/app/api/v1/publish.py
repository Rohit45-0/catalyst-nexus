"""
Publishing API
==============
POST /api/v1/publish/instagram   — Publish a poster/video URL to Instagram with tracking
POST /api/v1/publish/text         — Save a text item (tweet/blog/reel idea) to campaign history
GET  /api/v1/publish/campaigns    — List published campaigns
"""

import logging
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.base import get_db
from backend.app.db.models import User
from backend.app.services.publishing_service import PublishingService

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Schemas ─────────────────────────────────────────────────────────────────

class InstagramPublishRequest(BaseModel):
    media_url: str = Field(..., description="Public URL to the image/video to post")
    caption: str = Field(..., min_length=1, max_length=2200)
    campaign_id: Optional[str] = None
    add_tracking_link: bool = True


class InstagramPublishResponse(BaseModel):
    success: bool
    post_id: Optional[str] = None
    campaign_id: Optional[str] = None
    tracking_link: Optional[str] = None
    platform: str = "instagram"
    error: Optional[str] = None


class CampaignRecord(BaseModel):
    campaign_id: str
    platform: str
    post_id: Optional[str] = None
    tracking_link: Optional[str] = None
    created_at: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/instagram",
    response_model=InstagramPublishResponse,
    summary="Publish to Instagram with tracking link",
)
async def publish_to_instagram(
    body: InstagramPublishRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Publish a poster or video URL to Instagram. Automatically adds a tracking link to the caption."""
    svc = PublishingService(db)
    try:
        result = await svc.publish_to_instagram(
            media_url=body.media_url,
            caption=body.caption,
            campaign_id=body.campaign_id,
            user_id=current_user.id,
            add_tracking_link=body.add_tracking_link,
        )
        return InstagramPublishResponse(**result)
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception as exc:
        logger.error(f"Instagram publish failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Instagram publish failed: {str(exc)}",
        )


@router.get(
    "/campaigns",
    response_model=List[CampaignRecord],
    summary="List published campaigns",
)
async def list_published_campaigns(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """Return the most recent published campaigns for the current user."""
    svc = PublishingService(db)
    records = svc.list_campaigns(user_id=current_user.id, limit=limit)
    return [
        CampaignRecord(
            campaign_id=r.campaign_id,
            platform=r.platform,
            post_id=r.post_id,
            tracking_link=r.tracking_link,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in records
    ]
