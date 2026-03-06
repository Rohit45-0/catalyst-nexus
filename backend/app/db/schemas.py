"""
Pydantic Schemas
================

Request/response validation schemas for the API.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, ConfigDict


# =============================================================================
# Enums
# =============================================================================

class JobStatus(str, Enum):
    """Status of a generation job."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IdentityType(str, Enum):
    """Types of identities in the vault."""
    FACE = "face"
    CHARACTER = "character"
    STYLE = "style"
    OBJECT = "object"


class AssetType(str, Enum):
    """Types of assets."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"


# =============================================================================
# Auth Schemas
# =============================================================================

class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    user_id: Optional[str] = None
    email: Optional[str] = None


# =============================================================================
# User Schemas
# =============================================================================

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)


class UserResponse(UserBase):
    """User response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str] = None
    wallet_balance: int = 500
    created_at: datetime


# =============================================================================
# Project Schemas
# =============================================================================

class ProjectBase(BaseModel):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    settings: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    is_archived: Optional[bool] = None


class ProjectResponse(ProjectBase):
    """Project response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    owner_id: str
    settings: Dict[str, Any]
    thumbnail_url: Optional[str] = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Paginated project list response."""
    projects: List[ProjectResponse]
    total: int
    skip: int
    limit: int


# =============================================================================
# Asset Schemas
# =============================================================================

class AssetCreate(BaseModel):
    """Schema for creating an asset."""
    name: str
    asset_type: AssetType
    asset_metadata: Optional[Dict[str, Any]] = None


class AssetResponse(BaseModel):
    """Asset response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    asset_type: str
    storage_path: str
    storage_url: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    asset_metadata: Dict[str, Any]
    project_id: str
    created_at: datetime


# =============================================================================
# Identity Schemas
# =============================================================================

class IdentityBase(BaseModel):
    """Base identity schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    identity_type: IdentityType = IdentityType.FACE


class IdentityCreate(IdentityBase):
    """Schema for creating an identity."""
    metadata: Optional[Dict[str, Any]] = None


class IdentityUpdate(BaseModel):
    """Schema for updating an identity."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None


class IdentityResponse(IdentityBase):
    """Identity response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    source_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    features: Dict[str, Any]
    metadata: Dict[str, Any]
    user_id: str
    is_public: bool
    created_at: datetime
    updated_at: datetime


class IdentityListResponse(BaseModel):
    """Paginated identity list response."""
    identities: List[IdentityResponse]
    total: int
    skip: int
    limit: int


# =============================================================================
# Job Schemas
# =============================================================================

class JobBase(BaseModel):
    """Base job schema."""
    job_type: str = Field(..., description="Type of generation job")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class JobCreate(JobBase):
    """Schema for creating a job."""
    project_id: Optional[str] = None
    priority: Optional[int] = Field(5, ge=1, le=10)


class JobResponse(JobBase):
    """Job response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    status: JobStatus
    progress: int
    status_message: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    output_assets: List[str]
    user_id: str
    project_id: Optional[str] = None
    priority: int
    retry_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    """Paginated job list response."""
    jobs: List[JobResponse]
    total: int
    skip: int
    limit: int


# =============================================================================
# Generation Request Schemas
# =============================================================================

class ImageGenerationRequest(BaseModel):
    """Schema for image generation request."""
    prompt: str = Field(..., min_length=1, max_length=2000)
    negative_prompt: Optional[str] = Field(None, max_length=1000)
    width: int = Field(1024, ge=256, le=2048)
    height: int = Field(1024, ge=256, le=2048)
    quality: str = Field("standard", pattern="^(draft|standard|high|ultra)$")
    identity_id: Optional[str] = None
    seed: Optional[int] = None
    project_id: Optional[str] = None


class VideoGenerationRequest(BaseModel):
    """Schema for video generation request."""
    prompt: str = Field(..., min_length=1, max_length=2000)
    negative_prompt: Optional[str] = Field(None, max_length=1000)
    width: int = Field(1024, ge=256, le=2048)
    height: int = Field(576, ge=256, le=1152)
    duration: float = Field(5.0, ge=1.0, le=30.0)
    fps: int = Field(24, ge=12, le=60)
    motion_type: str = Field("moderate", pattern="^(static|subtle|moderate|dynamic|custom)$")
    camera_motion: str = Field("static", pattern="^(static|pan_left|pan_right|tilt_up|tilt_down|zoom_in|zoom_out|orbit)$")
    identity_id: Optional[str] = None
    seed: Optional[int] = None
    project_id: Optional[str] = None


class IdentityExtractionRequest(BaseModel):
    """Schema for identity extraction request."""
    name: str = Field(..., min_length=1, max_length=255)
    identity_type: IdentityType = IdentityType.FACE
    # File is uploaded separately as multipart form data


# Tracking System Schemas
class CampaignBase(BaseModel):
    """Base campaign schema."""
    campaign_id: str = Field(..., min_length=1, max_length=255)
    platform: str = "instagram"


class CampaignCreate(CampaignBase):
    """Schema for creating a campaign."""
    pass


class CampaignResponse(CampaignBase):
    """Campaign response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    post_id: Optional[str] = None
    publish_time: Optional[datetime] = None
    tracking_link: Optional[str] = None
    user_id: str
    created_at: datetime


class ClickEventBase(BaseModel):
    """Base click event schema."""
    campaign_id: str
    city: str
    country: str


class ClickEventResponse(ClickEventBase):
    """Click event response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    timestamp: datetime


class InsightSnapshotBase(BaseModel):
    """Base insight snapshot schema."""
    campaign_id: str
    city: Optional[str] = None
    reach: Optional[float] = None
    impressions: Optional[float] = None
    engagement: Optional[float] = None
    shares: Optional[float] = None
    saves: Optional[float] = None


class InsightSnapshotResponse(InsightSnapshotBase):
    """Insight snapshot response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    timestamp: datetime


class SpreadAnalysisResponse(BaseModel):
    """Response for spread analysis."""
    campaign: str
    nodes: List[str]
    edges: List[Dict[str, str]]
    trending: Optional[str] = None
    emerging: Optional[str] = None
# =============================================================================
# Market Intelligence Schemas
# =============================================================================

class GapAnalysisResult(BaseModel):
    """Result of a competitor gap analysis."""
    competitor: str
    top_questions: List[str]
    complaints: List[str]
    viral_hooks: List[str]
    opportunity_gap: str

class CompetitorAnalysisRequest(BaseModel):
    """Request schema for competitor analysis."""
    usernames: List[str]

class MarketIntelResponse(BaseModel):
    """Response schema for market intelligence analysis."""
    analyses: List[GapAnalysisResult]
    consolidated_strategy: str


class CategoryTrendRequest(BaseModel):
    """Request schema for category trend analysis."""
    category: str = Field(..., min_length=2, max_length=100)
    platform: str = Field(default="youtube", pattern="^(youtube|instagram)$")
    region_code: str = Field(default="IN", min_length=2, max_length=2)
    max_results: int = Field(default=10, ge=3, le=50)


class TrendPostInsight(BaseModel):
    """Normalized trend post/video insight."""
    platform: str
    post_id: str
    title: str
    url: str
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    engagement_rate: Optional[float] = None
    caption: Optional[str] = None


class CategoryTrendAnalysisResponse(BaseModel):
    """Response for category trend analysis."""
    category: str
    platform: str
    region_code: Optional[str] = None
    data_source: str
    top_posts: List[TrendPostInsight]
    top_keywords: List[str]
    recommended_hooks: List[str]
    content_gaps: List[str]
    posting_recommendations: List[str]
    generated_at: datetime


class ProductCampaignBriefRequest(BaseModel):
    """Request to generate campaign brief from product and trend context."""
    product_name: str = Field(..., min_length=2, max_length=200)
    product_description: str = Field(..., min_length=10, max_length=3000)
    category: str = Field(..., min_length=2, max_length=100)
    target_audience: str = Field(..., min_length=2, max_length=500)
    product_image_url: Optional[str] = Field(default=None, max_length=2000)
    product_image_name: Optional[str] = Field(default=None, max_length=255)
    identity_notes: Optional[str] = Field(default=None, max_length=1000)
    region_code: str = Field(default="IN", min_length=2, max_length=2)
    video_generation_enabled: bool = Field(default=False)
    system_prompt: Optional[str] = Field(default=None, max_length=5000)
    visual_dna: Optional[Dict[str, Any]] = Field(default=None, description="Extracted Visual DNA from product image")
    competitor_insights: Optional[List[Dict[str, Any]]] = Field(default=None, description="Competitor gap analysis results")


class BlogGenerationRequest(BaseModel):
    idea: str
    product_name: str
    campaign_strategy: str

class BlogGenerationResponse(BaseModel):
    blog_content: str

class ReelGenerationRequest(BaseModel):
    idea: str
    product_name: str
    campaign_id: Optional[str] = None

class ReelGenerationResponse(BaseModel):
    video_url: str
    asset_name: str


class CampaignGenerationResponse(BaseModel):
    """AI-generated campaign brief based on trend data."""
    category_trend_analysis: CategoryTrendAnalysisResponse
    campaign_strategy: str
    blog_ideas: List[str]
    tweet_ideas: List[str]
    reel_ideas: List[str]
    short_video_ideas: List[str]
    poster_ideas: List[str]


class FullCampaignPipelineRequest(BaseModel):
    """One-click full pipeline request for demo-ready campaign generation."""
    product_name: str = Field(..., min_length=2, max_length=200)
    product_description: str = Field(..., min_length=10, max_length=3000)
    category: str = Field(..., min_length=2, max_length=100)
    target_audience: str = Field(..., min_length=2, max_length=500)
    region_code: str = Field(default="IN", min_length=2, max_length=2)
    product_image_url: Optional[str] = Field(default=None, max_length=2000)
    product_image_name: Optional[str] = Field(default=None, max_length=255)
    product_image_data_url: Optional[str] = Field(default=None, max_length=2_000_000)
    identity_notes: Optional[str] = Field(default=None, max_length=1000)
    competitor_handles: List[str] = Field(default_factory=list)
    video_generation_enabled: bool = Field(default=True)
    poster_generation_count: int = Field(default=3, ge=1, le=5)
    video_duration_seconds: float = Field(default=8.0, ge=3.0, le=30.0)
    max_trend_results: int = Field(default=8, ge=3, le=20)
    system_prompt: Optional[str] = Field(default=None, max_length=5000)
    visual_dna_precomputed: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Pre-computed Visual DNA from progressive pipeline (skip extraction if present)",
    )


class AssetDownloadLink(BaseModel):
    """Downloadable generated asset descriptor."""
    name: str
    asset_type: str
    path: str
    download_url: str


class CampaignScoreBreakdown(BaseModel):
    """Scoring and ranking breakdown for AI campaign versus competitor baseline."""
    ai_score: float
    competitor_score: float
    uplift_percent: float
    verdict: str
    factors: List[str] = Field(default_factory=list)
    feature_vector: Dict[str, float] = Field(default_factory=dict)


class FullCampaignPipelineResponse(BaseModel):
    """End-to-end pipeline response including identity, intel, scores, and assets."""
    identity_vault: Dict[str, Any]
    market_intel: Dict[str, Any]
    gap_analysis: Dict[str, Any]
    competitor_matrix: List[Dict[str, Any]]
    scoring: CampaignScoreBreakdown
    campaign: CampaignGenerationResponse
    poster_assets: List[AssetDownloadLink] = Field(default_factory=list)
    video_asset: Optional[AssetDownloadLink] = None
    downloads: Dict[str, str] = Field(default_factory=dict)
    # Background job ID for media rendering — frontend tracks via WebSocket
    media_render_job_id: Optional[str] = None


class SystemPromptRequest(BaseModel):
    category: str = Field(..., min_length=2, max_length=100)
    product_name: Optional[str] = Field(None, max_length=200)


class SystemPromptResponse(BaseModel):
    system_prompt: str


class IdentityExtractionLiteRequest(BaseModel):
    """Lightweight request for extracting Visual DNA without creating a project."""
    product_name: str = Field(..., min_length=2, max_length=200)
    image_data_url: Optional[str] = Field(default=None, max_length=2_000_000)
    image_url: Optional[str] = Field(default=None, max_length=2000)
    identity_notes: Optional[str] = Field(default=None, max_length=1000)


class IdentityExtractionLiteResponse(BaseModel):
    """Lightweight response with just the Visual DNA dict."""
    status: str
    visual_dna: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    error: Optional[str] = None


class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: List[Dict[str, str]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    video_generation_enabled: bool = Field(default=False)


class AssistantChatResponse(BaseModel):
    reply: str
