"""
Generated Campaigns API
=======================
GET  /api/v1/campaigns/           — List all campaigns for the current user
GET  /api/v1/campaigns/{id}       — Get a specific campaign by ID
DELETE /api/v1/campaigns/{id}     — Delete a campaign
"""

import logging
from typing import Annotated, List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.security import get_current_user
from backend.app.db.base import get_db
from backend.app.db.models import User, GeneratedCampaign

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Response Schemas ─────────────────────────────────────────────────────────

class CampaignSummary(BaseModel):
    id: str
    product_name: str
    category: Optional[str] = None
    target_audience: Optional[str] = None
    region_code: Optional[str] = None
    campaign_strategy: Optional[str] = None
    blog_ideas: List[str] = []
    tweet_ideas: List[str] = []
    reel_ideas: List[str] = []
    short_video_ideas: List[str] = []
    poster_ideas: List[str] = []
    poster_assets: List[dict] = []
    scoring: Optional[dict] = None
    gap_analysis: Optional[dict] = None
    competitor_matrix: List[dict] = []
    trend_keywords: List[str] = []
    content_gaps: List[str] = []
    created_at: str

    class Config:
        from_attributes = True


def _serialize(row: GeneratedCampaign) -> CampaignSummary:
    return CampaignSummary(
        id=str(row.id),
        product_name=row.product_name or "",
        category=row.category,
        target_audience=row.target_audience,
        region_code=row.region_code,
        campaign_strategy=row.campaign_strategy,
        blog_ideas=row.blog_ideas or [],
        tweet_ideas=row.tweet_ideas or [],
        reel_ideas=row.reel_ideas or [],
        short_video_ideas=row.short_video_ideas or [],
        poster_ideas=row.poster_ideas or [],
        poster_assets=row.poster_assets or [],
        scoring=row.scoring,
        gap_analysis=row.gap_analysis,
        competitor_matrix=row.competitor_matrix or [],
        trend_keywords=row.trend_keywords or [],
        content_gaps=row.content_gaps or [],
        created_at=row.created_at.isoformat() + "Z" if row.created_at else datetime.utcnow().isoformat() + "Z",
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=List[CampaignSummary], summary="List generated campaigns")
async def list_campaigns(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Return all generated campaigns for the authenticated user, newest first."""
    rows = (
        db.query(GeneratedCampaign)
        .filter(GeneratedCampaign.user_id == current_user.id)
        .order_by(GeneratedCampaign.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_serialize(r) for r in rows]


@router.get("/{campaign_id}", response_model=CampaignSummary, summary="Get single campaign")
async def get_campaign(
    campaign_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    row = (
        db.query(GeneratedCampaign)
        .filter(
            GeneratedCampaign.id == campaign_id,
            GeneratedCampaign.user_id == current_user.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return _serialize(row)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete campaign")
async def delete_campaign(
    campaign_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    row = (
        db.query(GeneratedCampaign)
        .filter(
            GeneratedCampaign.id == campaign_id,
            GeneratedCampaign.user_id == current_user.id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    db.delete(row)
    db.commit()
