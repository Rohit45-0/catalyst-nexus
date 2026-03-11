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

class BotGenerateRequest(BaseModel):
    user_id: str
    type: str # video, poster, blog
    prompt: str
    phone_number: str
    phone_number_id: Optional[str] = None


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


@router.post("/generate-via-bot", summary="Trigger generation from WhatsApp Bot")
async def generate_via_bot(req: BotGenerateRequest):
    """Triggered by the Plugins service asynchronously when the owner texts the bot."""
    import asyncio
    import httpx
    
    async def bg_generate():
        try:
            from openai import AsyncOpenAI
            from backend.app.core.config import settings
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            gen_type = req.type.lower()
            webhook_url = "http://localhost:8001/api/v1/whatsapp/system-alert"
            # Hardcode to railway URL if deployed, assuming localhost for dev
            payload = {
                "user_id": req.user_id,
                "phone_number": req.phone_number,
                "phone_number_id": req.phone_number_id,
            }
            
            if "video" in gen_type:
                # Mock video URL mapping
                await asyncio.sleep(5)
                payload["video_url"] = "https://www.w3schools.com/html/mov_bbb.mp4"
                payload["message"] = f"Here is your AI generated {gen_type} for: '{req.prompt}'!\n\n(Note: Neural Render takes ~5 mins. Sending this preview MP4 for Demo purposes)."
                
            elif "poster" in gen_type or "image" in gen_type:
                # Generate DALL-E image
                res = await client.images.generate(
                    model="dall-e-3",
                    prompt=f"A beautiful promotional poster for a local business. Theme: {req.prompt}. Professional, high quality, eye-catching textless design.",
                    size="1024x1024",
                    quality="standard",
                    n=1
                )
                payload["image_url"] = res.data[0].url
                payload["message"] = f"Here is your AI generated {gen_type} for: '{req.prompt}'!"
                
            else: # blog or text
                res = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": f"Write a short, engaging promotional message/blog post for WhatsApp about: {req.prompt}"}],
                    max_tokens=600
                )
                payload["message"] = f"Here is your generated {gen_type} text:\n\n{res.choices[0].message.content}"
            
            # Send results back to plugins webhook
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                print("Sending generated alert to plugin webhook:", webhook_url)
                await http_client.post(webhook_url, json=payload)
                
        except Exception as e:
            logger.error(f"WhatsApp generation failed: {e}")
            try:
                async with httpx.AsyncClient(timeout=10.0) as http_client:
                    await http_client.post(webhook_url, json={
                        "user_id": req.user_id,
                        "phone_number": req.phone_number,
                        "phone_number_id": req.phone_number_id,
                        "message": f"❌ Failed to generate {req.type}. Error: {e}"
                    })
            except Exception as e2:
                print(f"Failed to send error alert: {e2}")

    # Launch background task
    asyncio.create_task(bg_generate())
    return {"status": "queued"}

