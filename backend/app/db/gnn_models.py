"""
GNN GRAPH DATABASE SCHEMA
=========================

NeoN Graph Database Design for Viral Spread Prediction

Based on your workflow images, this creates the proper schema for:
- Storing view/impression data (NOT clicks)
- Building graph for GNN training
- Tracking viral spread in real-time
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from backend.app.db.base import Base


class GraphNode(Base):
    """
    Represents a city node in the viral spread graph.
    
    Each node is a city where the post was VIEWED (from Instagram insights).
    """
    __tablename__ = "graph_nodes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Node identification
    city = Column(String, nullable=False)
    country = Column(String, nullable=False)
    
    # Campaign this node belongs to
    campaign_id = Column(String, ForeignKey('campaigns.campaign_id'), nullable=False)
    
    # Metrics (from Instagram API)
    impressions = Column(Integer, default=0)  # Total times shown
    reach = Column(Integer, default=0)  # Unique accounts reached
    engagement = Column(Integer, default=0)  # Likes + comments + shares
    profile_visits = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    
    # Temporal data
    first_seen = Column(DateTime, default=datetime.utcnow)  # When first impression logged
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # GNN features
    growth_rate = Column(Float, default=0.0)  # impressions growth rate
    engagement_rate = Column(Float, default=0.0)  # engagement / reach
    virality_score = Column(Float, default=0.0)  # Calculated score
    
    # Indexes for fast querying
    __table_args__ = (
        Index('idx_campaign_city', 'campaign_id', 'city'),
        Index('idx_first_seen', 'first_seen'),
    )


class GraphEdge(Base):
    """
    Represents spread from one city to another.
    
    Edge created when:
    - City B shows impressions AFTER City A
    - Indicates potential viral spread path
    """
    __tablename__ = "graph_edges"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Campaign
    campaign_id = Column(String, ForeignKey('campaigns.campaign_id'), nullable=False)
    
    # Directional edge: from_city → to_city
    from_city = Column(String, nullable=False)
    from_country = Column(String, nullable=False)
    to_city = Column(String, nullable=False)
    to_country = Column(String, nullable=False)
    
    # Edge properties
    time_delta = Column(Float, nullable=False)  # Seconds between first impressions
    weight = Column(Float, default=1.0)  # Edge strength (can be engagement ratio)
    confidence = Column(Float, default=0.5)  # Confidence this is a real spread path
    
    # Metrics at edge creation
    from_city_impressions = Column(Integer, default=0)
    to_city_impressions = Column(Integer, default=0)
    transfer_rate = Column(Float, default=0.0)  # to_impressions / from_impressions
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_campaign_edge', 'campaign_id', 'from_city', 'to_city'),
        Index('idx_time_delta', 'time_delta'),
    )


class ViralSpreadSnapshot(Base):
    """
    Time-series snapshots of viral spread.
    
    Captures state of graph at different times for GNN training.
    """
    __tablename__ = "viral_spread_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    campaign_id = Column(String, ForeignKey('campaigns.campaign_id'), nullable=False)
    
    # Snapshot time
    snapshot_time = Column(DateTime, default=datetime.utcnow)
    hours_since_publish = Column(Float, nullable=False)
    
    # Graph state at this time
    total_nodes = Column(Integer, default=0)  # Active cities
    total_edges = Column(Integer, default=0)  # Spread connections
    total_impressions = Column(Integer, default=0)
    total_reach = Column(Integer, default=0)
    total_engagement = Column(Integer, default=0)
    
    # Spread metrics
    geographic_spread = Column(Float, default=0.0)  # Distance covered
    velocity = Column(Float, default=0.0)  # Cities/hour
    trending_city = Column(String, nullable=True)
    emerging_cities = Column(String, nullable=True)  # JSON list
    
    # GNN prediction input
    graph_density = Column(Float, default=0.0)
    avg_node_degree = Column(Float, default=0.0)
    clustering_coefficient = Column(Float, default=0.0)
    
    # Index
    __table_args__ = (
        Index('idx_campaign_snapshot', 'campaign_id', 'snapshot_time'),
    )


class CategoryContentProfile(Base):
    """
    Aggregated transcript/content signals per category & locale.
    """
    __tablename__ = "category_content_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(String, nullable=False, unique=True)
    locale = Column(String, nullable=False, default="IN")

    top_keywords = Column(JSON, default=list)
    common_hook_lines = Column(JSON, default=list)
    common_cta_lines = Column(JSON, default=list)
    common_phrases = Column(JSON, default=list)

    sample_video_count = Column(Integer, default=0)
    avg_engagement_rate = Column(Float, default=0.0)
    last_data_source = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_category_profile_category', 'category'),
    )


class CampaignContentFeature(Base):
    """
    Campaign-level transcript/content feature snapshot for analytics + GNN.
    """
    __tablename__ = "campaign_content_features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(String, ForeignKey('campaigns.campaign_id'), nullable=False)
    category_profile_id = Column(UUID(as_uuid=True), ForeignKey('category_content_profiles.id'), nullable=True)

    category = Column(String, nullable=False)
    platform = Column(String, default="youtube")
    region_code = Column(String, default="IN")
    data_source = Column(String, nullable=True)

    sampled_video_ids = Column(JSON, default=list)
    sampled_video_titles = Column(JSON, default=list)
    transcript_video_count = Column(Integer, default=0)

    trend_keywords = Column(JSON, default=list)
    trend_hooks = Column(JSON, default=list)
    content_gaps = Column(JSON, default=list)
    transcript_phrases = Column(JSON, default=list)

    avg_views = Column(Float, default=0.0)
    avg_likes = Column(Float, default=0.0)
    avg_comments = Column(Float, default=0.0)
    avg_engagement_rate = Column(Float, default=0.0)
    hook_density = Column(Float, default=0.0)
    cta_density = Column(Float, default=0.0)

    feature_vector = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    is_training_ready = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_campaign_content_campaign', 'campaign_id'),
        Index('idx_campaign_content_category', 'category'),
    )


"""
USAGE:

1. When Instagram post published:
   - Create Campaign record

2. Every 15-30 minutes, fetch Instagram insights:
   - Get impressions per city
   - Create/update GraphNode for each city
   - Detect new cities (nodes)
   
3. Detect edges:
   - When new city appears, create GraphEdge from previous city
   - Calculate time_delta, weight, confidence
   
4. Create snapshots:
   - Every hour, create ViralSpreadSnapshot
   - Capture current graph state
   
5. Export for GNN training:
   - Nodes: graph_nodes table
   - Edges: graph_edges table
   - Time series: viral_spread_snapshots table
   
6. GNN learns to predict:
   - Which cities will activate next
   - How fast spread will occur
   - Final reach estimate
"""
