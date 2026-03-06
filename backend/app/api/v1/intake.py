"""
Product Intake API
==================
One-shot endpoint that handles the full Step 1 workflow:

  POST /intake/product
    ├── Creates (or reuses) a Project
    ├── Encodes the uploaded image to base64
    ├── Calls VisionDNAAgent (GPT-4o Vision) to extract Visual DNA
    ├── Saves ProductEmbedding in pgvector
    └── Returns the full DNA + project/embedding IDs

No public URL needed — the image is base64-encoded in memory.
"""

import base64
import logging
from pathlib import Path
from typing import Annotated, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agents.vision_dna import VisionDNAAgent, get_vision_dna_agent
from backend.app.core.security import get_current_user
from backend.app.db.base import get_db
from backend.app.db.models import ProductEmbedding, Project, User

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_MIME = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
MAX_SIZE_MB = 10


# ─── Response schema ─────────────────────────────────────────────────────────

class VisualDNAOut(BaseModel):
    product_category: str
    product_description: str
    materials: dict
    lighting: dict
    structure: dict
    motion_recommendations: list[str]
    camera_angle_suggestions: list[str]
    confidence_score: float


class ProductIntakeResponse(BaseModel):
    project_id: str
    embedding_id: str
    product_name: str
    version_label: str
    visual_dna: VisualDNAOut
    created_at: str


# ─── Endpoint ────────────────────────────────────────────────────────────────

@router.post(
    "/product",
    response_model=ProductIntakeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Product Intake — Full Step 1 Pipeline",
    description=(
        "Upload a product image + metadata. "
        "The backend creates a project, runs GPT-4o Vision to extract Visual DNA, "
        "and stores the embedding in the Identity Vault — all in one call."
    ),
)
async def product_intake(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    vision_agent: VisionDNAAgent = Depends(get_vision_dna_agent),
    # ── Form fields ──────────────────────────────────────────────────────────
    product_name: str = Form(..., description="Product name"),
    category: str = Form(..., description="Product category (e.g. Fashion, Tech, Beauty)"),
    target_audience: str = Form(..., description="Target audience description"),
    additional_context: Optional[str] = Form(None, description="Extra context for analysis"),
    # reuse existing project instead of creating a new one
    project_id: Optional[str] = Form(None, description="Existing project UUID (optional)"),
    # ── File ─────────────────────────────────────────────────────────────────
    image: UploadFile = File(..., description="Product image (JPEG/PNG/WEBP)"),
):
    logger.info(f"📦 Product intake for user={current_user.id}, product='{product_name}'")

    # ── Validate file ────────────────────────────────────────────────────────
    if image.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported image type '{image.content_type}'. Use JPEG, PNG or WEBP.",
        )

    image_bytes = await image.read()
    if len(image_bytes) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds {MAX_SIZE_MB} MB limit.",
        )

    # ── Encode image to base64 data URL ──────────────────────────────────────
    mime = image.content_type or "image/jpeg"
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime};base64,{b64}"

    # ── Resolve project ───────────────────────────────────────────────────────
    if project_id:
        project = db.execute(
            select(Project).where(
                Project.id == UUID(project_id),
                Project.owner_id == current_user.id,
            )
        ).scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found or access denied.",
            )
    else:
        project = Project(
            name=product_name,
            product_name=product_name,
            description=f"{category} — {target_audience}",
            owner_id=current_user.id,
            settings={"category": category, "target_audience": target_audience},
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info(f"✅ Created project {project.id}")

    # ── Extract Visual DNA ────────────────────────────────────────────────────
    context = f"Category: {category}. Target Audience: {target_audience}."
    if additional_context:
        context += f" {additional_context}"

    try:
        result = await vision_agent.extract_product_identity(
            image_sources=[data_url],
            product_name=product_name,
            additional_context=context,
        )
    except Exception as exc:
        logger.error(f"❌ Vision DNA extraction failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Visual DNA extraction failed: {str(exc)}",
        )

    # ── Store in Identity Vault ───────────────────────────────────────────────
    dna_dict = result.visual_dna.to_dict()
    embedding_record = ProductEmbedding(
        project_id=project.id,
        version_label="v1.0",
        visual_dna_json={
            **dna_dict,
            "product_name": product_name,
            "category": category,
            "target_audience": target_audience,
        },
        embedding_vector=result.embedding,
        is_active=True,
    )
    db.add(embedding_record)
    db.commit()
    db.refresh(embedding_record)
    logger.info(f"✅ Stored embedding {embedding_record.id}")

    return ProductIntakeResponse(
        project_id=str(project.id),
        embedding_id=str(embedding_record.id),
        product_name=product_name,
        version_label=embedding_record.version_label,
        visual_dna=VisualDNAOut(**dna_dict),
        created_at=embedding_record.created_at.isoformat(),
    )


# ─── List products for a user ─────────────────────────────────────────────────

@router.get(
    "/products",
    summary="List all products (projects) for the current user",
)
async def list_products(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Return all projects owned by the user, with their active embedding (if any)."""
    projects = db.execute(
        select(Project)
        .where(Project.owner_id == current_user.id)
        .order_by(Project.created_at.desc())
    ).scalars().all()

    result = []
    for p in projects:
        # Get the latest active embedding
        emb = db.execute(
            select(ProductEmbedding)
            .where(
                ProductEmbedding.project_id == p.id,
                ProductEmbedding.is_active == True,
            )
            .order_by(ProductEmbedding.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        dna = emb.visual_dna_json if emb else {}
        result.append({
            "project_id": str(p.id),
            "embedding_id": str(emb.id) if emb else None,
            "product_name": p.product_name or p.name,
            "category": dna.get("category", p.settings.get("category", "") if p.settings else ""),
            "target_audience": dna.get("target_audience", ""),
            "product_category": dna.get("product_category", ""),
            "confidence_score": dna.get("confidence_score", 0),
            "has_dna": emb is not None,
            "created_at": p.created_at.isoformat(),
        })

    return {"products": result, "total": len(result)}
