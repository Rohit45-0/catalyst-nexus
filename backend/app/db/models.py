import uuid

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, load_only
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from .base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Currency tracking in CENTS (500 = $5.00)
    wallet_balance = Column(Integer, default=500, nullable=False)
    # NOTE:
    # Some existing deployed/local DBs were created without users.updated_at.
    # Keeping this mapped causes auth registration/login flows to fail with
    # "column users.updated_at does not exist" on INSERT/refresh.
    # Add it back only after DB migration is guaranteed everywhere.

    @property
    def hashed_password(self) -> str:
        return self.password_hash

    @hashed_password.setter
    def hashed_password(self, value: str) -> None:
        self.password_hash = value

    @classmethod
    def get_by_email(cls, db, email: str):
        return (
            db.query(cls)
            .options(
                load_only(
                    cls.id,
                    cls.email,
                    cls.password_hash,
                    cls.is_active,
                    cls.created_at,
                )
            )
            .filter(cls.email == email)
            .first()
        )


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    product_name = Column(String, nullable=True)
    brand_name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    image_path = Column(String, nullable=True)

    # Backward-compatible fields expected by API schemas/routes
    name = Column(String, nullable=True)
    settings = Column(JSON, default=dict)
    is_archived = Column(Boolean, default=False)
    thumbnail_url = Column(String, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="project", cascade="all, delete-orphan")

    @property
    def owner_id(self):
        return self.user_id

    @owner_id.setter
    def owner_id(self, value):
        self.user_id = value


class ProductEmbedding(Base):
    """THE IDENTITY VAULT: Stores the mathematical Product DNA."""

    __tablename__ = "product_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    version_label = Column(String, default="v1.0")

    # Visual DNA (JSON traits + Vector Embedding)
    visual_dna_json = Column(JSON)
    embedding_vector = Column(Vector(1536))  # For OpenAI text-embedding-3-large

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    embedding_id = Column(UUID(as_uuid=True), ForeignKey("product_embeddings.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    job_type = Column(String, nullable=False)
    status = Column(String, default="pending")

    # Legacy/new payload compatibility
    parameters = Column(JSON, default=dict)
    input_payload = Column(JSON)
    result = Column(JSON)
    output_payload = Column(JSON)
    output_assets = Column(JSON, default=list)

    progress = Column(Integer, default=0)
    status_message = Column(String, nullable=True)
    error = Column(String, nullable=True)
    priority = Column(Integer, default=5)
    retry_count = Column(Integer, default=0)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    project = relationship("Project", back_populates="jobs")


class Asset(Base):
    """Asset model for files."""

    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)  # image, video, etc.
    storage_path = Column(String)
    storage_url = Column(String)
    file_size = Column(Float)
    mime_type = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    duration = Column(Float)
    asset_metadata = Column(JSON, default=dict)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    created_at = Column(DateTime, server_default=func.now())

    project = relationship("Project", back_populates="assets")


# Tracking System Models
class Campaign(Base):
    """Campaign record for tracking Instagram posts."""

    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(String, unique=True, nullable=False)  # e.g., ig_launch_001
    platform = Column(String, default="instagram")
    post_id = Column(String, nullable=True)  # Instagram post ID
    publish_time = Column(DateTime, nullable=True)
    tracking_link = Column(String, nullable=True)  # https://yourdomain.com/p/{campaign_id}
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # GNN Context [NEW]
    category = Column(String, default="General")  # Tech, Fashion, Finance, etc.
    content_features = Column(JSON, nullable=True)  # 8-dim transcript feature vector
    
    created_at = Column(DateTime, server_default=func.now())


class ClickEvent(Base):
    """Anonymous click events from tracking links."""

    __tablename__ = "click_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=False)
    city = Column(String, nullable=False)
    country = Column(String, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())


class InsightSnapshot(Base):
    """Instagram insights snapshots."""

    __tablename__ = "insight_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=False)
    timestamp = Column(DateTime, server_default=func.now())
    city = Column(String, nullable=True)
    reach = Column(Float, nullable=True)
    impressions = Column(Float, nullable=True)
    engagement = Column(Float, nullable=True)
    shares = Column(Float, nullable=True)
    saves = Column(Float, nullable=True)
    
    # Tracking spread velocity [NEW]
    content_boost = Column(Float, default=1.0)  # Calculated from content_features


class GeneratedCampaign(Base):
    """Persists the full output of the /full-pipeline endpoint.

    - Text content (ideas, strategy, scoring) is stored as JSON columns.
    - Poster asset metadata (name, download_url, asset_type) is stored as JSON.
    - Video assets are NOT stored here — they live on the local filesystem and
      their paths are ephemeral. A future upgrade can upload them to Azure Blob
      or S3 and store the remote URL here.
    """

    __tablename__ = "generated_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    # ── Product context ────────────────────────────────────────────────────
    product_name = Column(String, nullable=False)
    product_description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    target_audience = Column(String, nullable=True)
    region_code = Column(String(8), nullable=True)

    # ── Generated content ──────────────────────────────────────────────────
    campaign_strategy = Column(Text, nullable=True)
    blog_ideas = Column(JSON, default=list)       # List[str]
    tweet_ideas = Column(JSON, default=list)
    reel_ideas = Column(JSON, default=list)
    short_video_ideas = Column(JSON, default=list)  # Empty when video OFF
    poster_ideas = Column(JSON, default=list)

    # ── Assets (metadata only, not binary) ────────────────────────────────
    poster_assets = Column(JSON, default=list)    # List[{name, download_url, asset_type}]
    # video_asset deliberately omitted — stored locally, not in DB

    # ── Analytics ─────────────────────────────────────────────────────────
    scoring = Column(JSON, nullable=True)         # CampaignScoreBreakdown dict
    competitor_matrix = Column(JSON, default=list)
    gap_analysis = Column(JSON, nullable=True)

    # ── Trend signals ─────────────────────────────────────────────────────
    trend_keywords = Column(JSON, default=list)
    content_gaps = Column(JSON, default=list)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class KnowledgeChunk(Base):
    """
    RAG Knowledge Base
    Stores semantic chunks of generated insights, brand voice, and market data.
    Used for retrieval-augmented generation in chat and future campaigns.
    """
    __tablename__ = "knowledge_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    # Content & Search
    content = Column(Text, nullable=False)  # The text chunk
    embedding = Column(Vector(1536))        # OpenAI text-embedding-3-small
    
    # Metadata for filtering
    category = Column(String, index=True)   # e.g., "market_intel", "brand_voice", "camp_history"
    source_type = Column(String)            # "campaign_generation", "user_edit", "web_search"
    source_id = Column(String, nullable=True) # ID of the campaign/post this came from
    
    # Ranking
    confidence_score = Column(Float, default=1.0)
    
    created_at = Column(DateTime, server_default=func.now())
