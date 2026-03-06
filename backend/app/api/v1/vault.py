"""
Identity Vault API Endpoints
============================

The "Geometric Lock" storage system - manages product embeddings 
for zero-shot consistent video generation.

Endpoints:
- POST /vault/products - Extract & store product identity
- GET /vault/products/{id} - Retrieve product by ID  
- GET /vault/products/{id}/versions - Get all versions
- POST /vault/products/search - Vector similarity search
- DELETE /vault/products/{id} - Remove product identity
"""

from typing import Annotated, List, Optional, Dict, Any
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from pydantic import BaseModel, Field

from backend.app.agents.vision_dna import VisionDNAAgent, get_vision_dna_agent
from backend.app.core.security import get_current_user
from backend.app.db.base import get_db
from backend.app.db.models import ProductEmbedding, Project, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vault", tags=["Identity Vault"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class ProductIdentityCreate(BaseModel):
    """Request schema for creating a product identity."""
    project_id: UUID
    product_name: str = Field(..., min_length=1, max_length=255)
    image_urls: List[str] = Field(..., min_items=1, max_items=10)
    additional_context: Optional[str] = None
    version_label: Optional[str] = "v1.0"


class VisualDNAResponse(BaseModel):
    """Visual DNA extracted from product images."""
    product_category: str
    product_description: str
    materials: Dict[str, Any]
    lighting: Dict[str, Any]
    structure: Dict[str, Any]
    motion_recommendations: List[str]
    camera_angle_suggestions: List[str]
    confidence_score: float


class ProductIdentityResponse(BaseModel):
    """Response schema for product identity."""
    id: UUID
    project_id: UUID
    version_label: str
    visual_dna: VisualDNAResponse
    source_images: List[str]
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True


class ProductSearchRequest(BaseModel):
    """Request schema for similarity search."""
    project_id: Optional[UUID] = None
    query_image_url: Optional[str] = None
    query_embedding: Optional[List[float]] = None
    top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class SimilarProductResponse(BaseModel):
    """Response for a similar product."""
    id: UUID
    version_label: str
    similarity_score: float
    product_category: str


class ProductSearchResponse(BaseModel):
    """Response schema for similarity search."""
    query_processed: bool
    results: List[SimilarProductResponse]
    total_found: int


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post(
    "/products",
    response_model=ProductIdentityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Extract & Store Product Identity",
    description="Analyze product images with GPT-4o Vision and store the Geometric Lock embedding."
)
async def create_product_identity(
    request: ProductIdentityCreate,
    db: Session = Depends(get_db),
    vision_agent: VisionDNAAgent = Depends(get_vision_dna_agent)
):
    """
    Create a new product identity (Geometric Lock) in the vault.
    
    This endpoint:
    1. Sends images to GPT-4o Vision for analysis
    2. Extracts material, lighting, and structural properties
    3. Generates a 1536-dim embedding vector
    4. Stores everything in PostgreSQL with pgvector
    
    Args:
        request: Product identity creation request
        db: Database session
        vision_agent: Vision DNA agent instance
        
    Returns:
        ProductIdentityResponse with the extracted identity
    """
    logger.info(f"🔐 Creating product identity for project {request.project_id}")
    
    # Verify project exists
    project_result = db.execute(
        select(Project).where(Project.id == request.project_id)
    )
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {request.project_id} not found"
        )
    
    try:
        # Extract identity using Vision DNA Agent
        extraction_result = await vision_agent.extract_product_identity(
            image_sources=request.image_urls,
            product_name=request.product_name,
            additional_context=request.additional_context
        )
        
        # Create database record
        product_embedding = ProductEmbedding(
            project_id=request.project_id,
            version_label=request.version_label,
            visual_dna_json={
                **extraction_result.visual_dna.to_dict(),
                "source_images": request.image_urls,
                "product_name": request.product_name,
            },
            embedding_vector=extraction_result.embedding,
            is_active=True
        )
        
        db.add(product_embedding)
        db.commit()
        db.refresh(product_embedding)
        
        logger.info(f"✅ Product identity created: {product_embedding.id}")
        
        return ProductIdentityResponse(
            id=product_embedding.id,
            project_id=product_embedding.project_id,
            version_label=product_embedding.version_label,
            visual_dna=VisualDNAResponse(**extraction_result.visual_dna.to_dict()),
            source_images=request.image_urls,
            is_active=product_embedding.is_active,
            created_at=product_embedding.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to create product identity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Identity extraction failed: {str(e)}"
        )


@router.get(
    "/products/{product_id}",
    response_model=ProductIdentityResponse,
    summary="Get Product Identity",
    description="Retrieve a specific product identity by ID."
)
async def get_product_identity(
    product_id: UUID,
    db: Session = Depends(get_db)
):
    """Retrieve a product identity from the vault."""
    
    result = db.execute(
        select(ProductEmbedding).where(ProductEmbedding.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product identity {product_id} not found"
        )
    
    visual_dna = product.visual_dna_json or {}
    
    return ProductIdentityResponse(
        id=product.id,
        project_id=product.project_id,
        version_label=product.version_label,
        visual_dna=VisualDNAResponse(
            product_category=visual_dna.get("product_category", ""),
            product_description=visual_dna.get("product_description", ""),
            materials=visual_dna.get("materials", {}),
            lighting=visual_dna.get("lighting", {}),
            structure=visual_dna.get("structure", {}),
            motion_recommendations=visual_dna.get("motion_recommendations", []),
            camera_angle_suggestions=visual_dna.get("camera_angle_suggestions", []),
            confidence_score=visual_dna.get("confidence_score", 0.0)
        ),
        source_images=visual_dna.get("source_images", []),
        is_active=product.is_active,
        created_at=product.created_at.isoformat()
    )


@router.get(
    "/products/{project_id}/versions",
    response_model=List[ProductIdentityResponse],
    summary="Get All Product Versions",
    description="Retrieve all identity versions for a project."
)
async def get_product_versions(
    project_id: UUID,
    include_inactive: bool = Query(False, description="Include deactivated versions"),
    db: Session = Depends(get_db)
):
    """Get all product identity versions for a project."""
    
    query = select(ProductEmbedding).where(
        ProductEmbedding.project_id == project_id
    )
    
    if not include_inactive:
        query = query.where(ProductEmbedding.is_active == True)
    
    query = query.order_by(ProductEmbedding.created_at.desc())
    
    result = db.execute(query)
    products = result.scalars().all()
    
    responses = []
    for product in products:
        visual_dna = product.visual_dna_json or {}
        responses.append(ProductIdentityResponse(
            id=product.id,
            project_id=product.project_id,
            version_label=product.version_label,
            visual_dna=VisualDNAResponse(
                product_category=visual_dna.get("product_category", ""),
                product_description=visual_dna.get("product_description", ""),
                materials=visual_dna.get("materials", {}),
                lighting=visual_dna.get("lighting", {}),
                structure=visual_dna.get("structure", {}),
                motion_recommendations=visual_dna.get("motion_recommendations", []),
                camera_angle_suggestions=visual_dna.get("camera_angle_suggestions", []),
                confidence_score=visual_dna.get("confidence_score", 0.0)
            ),
            source_images=visual_dna.get("source_images", []),
            is_active=product.is_active,
            created_at=product.created_at.isoformat()
        ))
    
    return responses


@router.post(
    "/products/search",
    response_model=ProductSearchResponse,
    summary="Vector Similarity Search",
    description="Find similar products using pgvector cosine similarity."
)
async def search_similar_products(
    request: ProductSearchRequest,
    db: Session = Depends(get_db),
    vision_agent: VisionDNAAgent = Depends(get_vision_dna_agent)
):
    """
    Search for similar products using vector similarity.
    
    You can search by:
    1. Providing an image URL (will extract embedding first)
    2. Providing a pre-computed embedding vector
    
    Returns products sorted by similarity score.
    """
    
    # Get query embedding
    if request.query_embedding:
        query_embedding = request.query_embedding
    elif request.query_image_url:
        # Extract embedding from image
        extraction = await vision_agent.extract_product_identity(
            image_sources=[request.query_image_url],
            product_name="Search Query"
        )
        query_embedding = extraction.embedding
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either query_image_url or query_embedding"
        )
    
    # Build query with pgvector similarity
    # Using cosine distance: 1 - (a <=> b) gives similarity
    from sqlalchemy import text
    
    # Base query
    base_conditions = []
    if request.project_id:
        base_conditions.append(f"project_id = '{request.project_id}'")
    base_conditions.append("is_active = true")
    
    where_clause = " AND ".join(base_conditions) if base_conditions else "1=1"
    
    # Convert embedding to PostgreSQL array format
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
    
    sql = text(f"""
        SELECT 
            id,
            version_label,
            visual_dna_json,
            1 - (embedding_vector <=> :embedding::vector) as similarity
        FROM product_embeddings
        WHERE {where_clause}
        AND 1 - (embedding_vector <=> :embedding::vector) >= :threshold
        ORDER BY similarity DESC
        LIMIT :limit
    """)
    
    result = db.execute(
        sql,
        {
            "embedding": embedding_str,
            "threshold": request.similarity_threshold,
            "limit": request.top_k
        }
    )
    
    rows = result.fetchall()
    
    results = []
    for row in rows:
        visual_dna = row.visual_dna_json or {}
        results.append(SimilarProductResponse(
            id=row.id,
            version_label=row.version_label,
            similarity_score=float(row.similarity),
            product_category=visual_dna.get("product_category", "Unknown")
        ))
    
    return ProductSearchResponse(
        query_processed=True,
        results=results,
        total_found=len(results)
    )


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Product Identity",
    description="Soft-delete a product identity (marks as inactive)."
)
async def delete_product_identity(
    product_id: UUID,
    hard_delete: bool = Query(False, description="Permanently delete instead of soft-delete"),
    db: Session = Depends(get_db)
):
    """Delete or deactivate a product identity."""
    
    result = db.execute(
        select(ProductEmbedding).where(ProductEmbedding.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product identity {product_id} not found"
        )
    
    if hard_delete:
        db.delete(product)
        logger.info(f"🗑️ Hard deleted product identity: {product_id}")
    else:
        product.is_active = False
        logger.info(f"📦 Soft deleted product identity: {product_id}")
    
    db.commit()


@router.patch(
    "/products/{product_id}/activate",
    response_model=ProductIdentityResponse,
    summary="Reactivate Product Identity",
    description="Reactivate a previously deactivated product identity."
)
async def activate_product_identity(
    product_id: UUID,
    db: Session = Depends(get_db)
):
    """Reactivate a soft-deleted product identity."""
    
    result = db.execute(
        select(ProductEmbedding).where(ProductEmbedding.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product identity {product_id} not found"
        )
    
    product.is_active = True
    db.commit()
    db.refresh(product)
    
    visual_dna = product.visual_dna_json or {}
    
    return ProductIdentityResponse(
        id=product.id,
        project_id=product.project_id,
        version_label=product.version_label,
        visual_dna=VisualDNAResponse(
            product_category=visual_dna.get("product_category", ""),
            product_description=visual_dna.get("product_description", ""),
            materials=visual_dna.get("materials", {}),
            lighting=visual_dna.get("lighting", {}),
            structure=visual_dna.get("structure", {}),
            motion_recommendations=visual_dna.get("motion_recommendations", []),
            camera_angle_suggestions=visual_dna.get("camera_angle_suggestions", []),
            confidence_score=visual_dna.get("confidence_score", 0.0)
        ),
        source_images=visual_dna.get("source_images", []),
        is_active=product.is_active,
        created_at=product.created_at.isoformat()
    )


@router.get(
    "/health",
    summary="Vault Health Check",
    description="Check if the Identity Vault is operational."
)
async def vault_health_check(db: Session = Depends(get_db)):
    """Health check for the Identity Vault."""
    try:
        # Test database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        
        # Count embeddings
        result = db.execute(
            select(ProductEmbedding).limit(1)
        )
        
        return {
            "status": "healthy",
            "service": "Identity Vault",
            "database": "connected",
            "vector_extension": "pgvector"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Vault unhealthy: {str(e)}"
        )


@router.get(
    "/identities",
    summary="Compatibility Identity List",
    description="Compatibility endpoint for legacy clients/tests.",
)
async def list_identities_compat(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """Compatibility endpoint returning an empty list for legacy identity path."""
    return {"identities": [], "total": 0, "skip": 0, "limit": 0}
