"""
Analytics Service
=================

Handles fetching and analyzing social media analytics.
"""

from typing import Optional, Dict, List
from datetime import datetime, timedelta
import logging
import re
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db.models import Campaign, ClickEvent, InsightSnapshot
from backend.app.db.gnn_models import CategoryContentProfile, CampaignContentFeature
from backend.app.services.tracking.instagram.publisher import InstagramPublisher
from backend.app.services.tracking.analytics.spike_detector import SpikeDetector
from backend.app.services.tracking.analytics.spread_graph import SpreadGraph

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics collection and analysis."""
    
    def __init__(self, db: Session):
        self.db = db
        self.instagram_publisher = InstagramPublisher()
        self.spike_detector = SpikeDetector(db)
        self.spread_graph = SpreadGraph(db)

    _CATEGORY_HASHTAGS = {
        "tech": ["tech", "gadgets", "ai", "innovation"],
        "fashion": ["fashion", "style", "outfit", "streetstyle"],
        "finance": ["finance", "investing", "moneymindset", "stockmarket"],
        "fitness": ["fitness", "workout", "healthylifestyle", "gym"],
        "food": ["food", "foodie", "recipe", "chef"],
    }
    
    async def fetch_and_store_insights(self, campaign_id: str) -> Dict:
        """
        Fetch insights from Instagram and store in database.
        
        Args:
            campaign_id: Campaign ID to fetch insights for
            
        Returns:
            Dictionary with fetched insights
        """
        try:
            # Get campaign
            campaign = self.db.query(Campaign).filter(
                Campaign.campaign_id == campaign_id
            ).first()
            
            if not campaign:
                raise ValueError(f"Campaign {campaign_id} not found")
            
            if not campaign.post_id:
                raise ValueError(f"Campaign {campaign_id} has no post_id")
            
            # Fetch insights from Instagram
            insights_data = self.instagram_publisher.get_post_insights(campaign.post_id)
            
            if not insights_data:
                logger.warning(f"No insights data returned for post {campaign.post_id}")
                return {"success": False, "error": "No insights data available"}
            
            # Parse insights
            insights = {}
            for metric in insights_data.get("data", []):
                insights[metric["name"]] = metric.get("values", [{}])[0].get("value", 0)
            
            # Store snapshot
            snapshot = InsightSnapshot(
                campaign_id=campaign_id,
                timestamp=datetime.utcnow(),
                city=None,  # Global insights
                reach=insights.get("reach", 0),
                impressions=insights.get("impressions", 0),
                engagement=insights.get("engagement", 0),
                shares=insights.get("shares", 0),
                saves=insights.get("saves", 0)
            )
            self.db.add(snapshot)
            self.db.commit()
            
            logger.info(f"✅ Stored insights for campaign {campaign_id}")
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "insights": insights,
                "timestamp": snapshot.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch insights for {campaign_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def fetch_all_campaign_insights(self, user_id: Optional[int] = None) -> List[Dict]:
        """Fetch insights for all active campaigns."""
        query = self.db.query(Campaign).filter(Campaign.post_id.isnot(None))
        
        if user_id:
            query = query.filter(Campaign.user_id == user_id)
        
        campaigns = query.all()
        results = []
        
        for campaign in campaigns:
            result = await self.fetch_and_store_insights(campaign.campaign_id)
            results.append(result)
        
        return results
    
    def get_campaign_analytics(self, campaign_id: str) -> Dict:
        """
        Get comprehensive analytics for a campaign.
        
        Returns:
            - Basic metrics (clicks, reach, engagement)
            - Spread analysis
            - Spikes detected
            - Geographic distribution
        """
        campaign = self.db.query(Campaign).filter(
            Campaign.campaign_id == campaign_id
        ).first()
        
        if not campaign:
            return {"error": "Campaign not found"}
        
        # Get click events
        clicks = self.db.query(ClickEvent).filter(
            ClickEvent.campaign_id == campaign_id
        ).all()
        
        # Get latest insights
        latest_insight = self.db.query(InsightSnapshot).filter(
            InsightSnapshot.campaign_id == campaign_id
        ).order_by(InsightSnapshot.timestamp.desc()).first()
        
        # Geographic distribution
        geo_distribution = self.db.query(
            ClickEvent.country,
            ClickEvent.city,
            func.count(ClickEvent.id).label('count')
        ).filter(
            ClickEvent.campaign_id == campaign_id
        ).group_by(ClickEvent.country, ClickEvent.city).all()
        
        # Detect spikes
        spikes = self.spike_detector.detect_spikes(campaign_id)
        
        # Get spread graph
        spread_data = self.spread_graph.analyze_spread(campaign_id)
        
        return {
            "campaign_id": campaign_id,
            "platform": campaign.platform,
            "post_id": campaign.post_id,
            "publish_time": campaign.publish_time.isoformat() if campaign.publish_time else None,
            "metrics": {
                "total_clicks": len(clicks),
                "reach": latest_insight.reach if latest_insight else 0,
                "impressions": latest_insight.impressions if latest_insight else 0,
                "engagement": latest_insight.engagement if latest_insight else 0,
                "shares": latest_insight.shares if latest_insight else 0,
                "saves": latest_insight.saves if latest_insight else 0,
            },
            "geographic_distribution": [
                {
                    "country": item.country,
                    "city": item.city,
                    "clicks": item.count
                }
                for item in geo_distribution
            ],
            "spikes": {
                "detected_cities": spikes,
                "count": len(spikes)
            },
            "spread_analysis": spread_data,
            "latest_insight_time": latest_insight.timestamp.isoformat() if latest_insight else None
        }
    
    def get_analytics_dashboard(self, user_id: Optional[int] = None, days: int = 7) -> Dict:
        """
        Get dashboard analytics for all campaigns.
        
        Args:
            user_id: Optional user filter
            days: Number of days to analyze
            
        Returns:
            Dashboard summary with aggregated metrics
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        # Get campaigns
        query = self.db.query(Campaign).filter(Campaign.created_at >= since)
        if user_id:
            query = query.filter(Campaign.user_id == user_id)
        
        campaigns = query.all()
        
        # Aggregate metrics
        total_clicks = 0
        total_reach = 0
        total_engagement = 0
        campaign_summaries = []
        
        for campaign in campaigns:
            # Count clicks
            click_count = self.db.query(func.count(ClickEvent.id)).filter(
                ClickEvent.campaign_id == campaign.campaign_id
            ).scalar()
            
            # Get latest insight
            latest_insight = self.db.query(InsightSnapshot).filter(
                InsightSnapshot.campaign_id == campaign.campaign_id
            ).order_by(InsightSnapshot.timestamp.desc()).first()
            
            reach = latest_insight.reach if latest_insight else 0
            engagement = latest_insight.engagement if latest_insight else 0
            
            total_clicks += click_count or 0
            total_reach += reach or 0
            total_engagement += engagement or 0
            
            campaign_summaries.append({
                "campaign_id": campaign.campaign_id,
                "platform": campaign.platform,
                "clicks": click_count,
                "reach": reach,
                "engagement": engagement,
                "publish_time": campaign.publish_time.isoformat() if campaign.publish_time else None
            })
        
        # Get top performing campaigns
        top_campaigns = sorted(
            campaign_summaries,
            key=lambda x: x.get("engagement", 0),
            reverse=True
        )[:5]
        
        return {
            "period_days": days,
            "total_campaigns": len(campaigns),
            "aggregate_metrics": {
                "total_clicks": total_clicks,
                "total_reach": total_reach,
                "total_engagement": total_engagement,
                "avg_engagement_per_campaign": total_engagement / len(campaigns) if campaigns else 0
            },
            "top_campaigns": top_campaigns,
            "all_campaigns": campaign_summaries
        }
    
    def get_click_timeline(self, campaign_id: str) -> List[Dict]:
        """Get timeline of clicks for a campaign."""
        clicks = self.db.query(ClickEvent).filter(
            ClickEvent.campaign_id == campaign_id
        ).order_by(ClickEvent.timestamp).all()
        
        return [
            {
                "timestamp": click.timestamp.isoformat(),
                "city": click.city,
                "country": click.country
            }
            for click in clicks
        ]

    def get_competitor_content_intel(self, limit: int = 5) -> Dict:
        """Return content pattern intel from stored category/trend feature tables."""
        profiles = self.db.query(CategoryContentProfile).order_by(CategoryContentProfile.updated_at.desc()).limit(limit).all()
        features = self.db.query(CampaignContentFeature).order_by(CampaignContentFeature.created_at.desc()).limit(limit).all()

        return {
            "profiles": [
                {
                    "category": p.category,
                    "locale": p.locale,
                    "top_keywords": (p.top_keywords or [])[:8],
                    "common_hook_lines": (p.common_hook_lines or [])[:5],
                    "avg_engagement_rate": p.avg_engagement_rate or 0,
                    "sample_video_count": p.sample_video_count or 0,
                }
                for p in profiles
            ],
            "recent_features": [
                {
                    "category": f.category,
                    "platform": f.platform,
                    "trend_keywords": (f.trend_keywords or [])[:8],
                    "trend_hooks": (f.trend_hooks or [])[:5],
                    "avg_engagement_rate": f.avg_engagement_rate or 0,
                }
                for f in features
            ],
        }

    def ingest_trending_reels_by_category(
        self,
        category: str,
        limit_per_hashtag: int = 20,
        locale: str = "IN",
    ) -> Dict:
        """
        Pull trending Instagram Reel/video metadata by category hashtags
        and store aggregated features for downstream GNN training.
        """
        normalized_category = category.strip().lower()
        hashtags = self._CATEGORY_HASHTAGS.get(normalized_category, [normalized_category, "trending", "viral"])

        collected_media: List[Dict] = []
        for hashtag in hashtags:
            hashtag_id = self.instagram_publisher.get_hashtag_id(hashtag)
            if not hashtag_id:
                continue
            media = self.instagram_publisher.get_recent_hashtag_media(hashtag_id, limit=limit_per_hashtag)
            for item in media:
                item["_source_hashtag"] = hashtag
            collected_media.extend(media)

        if not collected_media:
            return {
                "success": False,
                "category": category,
                "message": "No hashtag media available (check token permissions/business account access).",
                "hashtags": hashtags,
            }

        captions = [str(item.get("caption", "") or "") for item in collected_media]
        keyword_counts = Counter()
        for caption in captions:
            keyword_counts.update(self._extract_keywords(caption))

        top_keywords = [kw for kw, _ in keyword_counts.most_common(20)]
        hooks = [c.strip()[:160] for c in captions if c.strip()][:12]
        avg_likes = sum(float(item.get("like_count", 0) or 0) for item in collected_media) / len(collected_media)
        avg_comments = sum(float(item.get("comments_count", 0) or 0) for item in collected_media) / len(collected_media)
        avg_engagement = (avg_likes + avg_comments)

        profile = self.db.query(CategoryContentProfile).filter(
            CategoryContentProfile.category == normalized_category
        ).first()
        if not profile:
            profile = CategoryContentProfile(
                category=normalized_category,
                locale=locale,
                top_keywords=top_keywords,
                common_hook_lines=hooks,
                common_cta_lines=self._extract_cta_lines(captions),
                common_phrases=self._extract_common_phrases(captions),
                sample_video_count=len(collected_media),
                avg_engagement_rate=avg_engagement,
                last_data_source="instagram_graph_hashtag",
            )
            self.db.add(profile)
            self.db.flush()
        else:
            profile.top_keywords = top_keywords
            profile.common_hook_lines = hooks
            profile.common_cta_lines = self._extract_cta_lines(captions)
            profile.common_phrases = self._extract_common_phrases(captions)
            profile.sample_video_count = len(collected_media)
            profile.avg_engagement_rate = avg_engagement
            profile.last_data_source = "instagram_graph_hashtag"

        feature_row = CampaignContentFeature(
            campaign_id=f"trend_{normalized_category}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            category_profile_id=profile.id,
            category=normalized_category,
            platform="instagram",
            region_code=locale,
            data_source="instagram_graph_hashtag",
            sampled_video_ids=[m.get("id") for m in collected_media if m.get("id")],
            sampled_video_titles=[(m.get("caption") or "").strip()[:120] for m in collected_media],
            transcript_video_count=len(collected_media),
            trend_keywords=top_keywords,
            trend_hooks=hooks,
            content_gaps=[],
            transcript_phrases=self._extract_common_phrases(captions),
            avg_views=0.0,
            avg_likes=avg_likes,
            avg_comments=avg_comments,
            avg_engagement_rate=avg_engagement,
            hook_density=float(len(hooks)) / max(1.0, len(collected_media)),
            cta_density=float(len(profile.common_cta_lines or [])) / max(1.0, len(collected_media)),
            feature_vector=[],
            notes="Auto-ingested from Instagram hashtag reels/media",
            is_training_ready=True,
        )
        self.db.add(feature_row)
        self.db.commit()

        return {
            "success": True,
            "category": category,
            "hashtags": hashtags,
            "media_count": len(collected_media),
            "top_keywords": top_keywords[:10],
            "profile_id": str(profile.id),
            "feature_row_id": str(feature_row.id),
        }

    def _extract_keywords(self, text: str) -> List[str]:
        stop = {"the", "and", "for", "with", "that", "this", "you", "your", "are", "from"}
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", text.lower())
        return [t for t in tokens if t not in stop]

    def _extract_cta_lines(self, captions: List[str]) -> List[str]:
        cta_tokens = ("follow", "comment", "share", "save", "link", "dm", "buy", "shop")
        result: List[str] = []
        for cap in captions:
            for line in cap.splitlines():
                low = line.lower()
                if any(token in low for token in cta_tokens):
                    cleaned = line.strip()
                    if cleaned:
                        result.append(cleaned[:160])
        return result[:20]

    def _extract_common_phrases(self, captions: List[str]) -> List[str]:
        tokens: List[str] = []
        for cap in captions:
            parts = self._extract_keywords(cap)
            tokens.extend(parts)
        counts = Counter(tokens)
        return [w for w, _ in counts.most_common(20)]
