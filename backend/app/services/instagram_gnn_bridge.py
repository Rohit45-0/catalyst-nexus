"""
INSTAGRAM TO GNN BRIDGE
=======================

Bridges REAL Instagram post performance (city-level reach) into GNN training data.

This service:
1.  Fetches a published Instagram post's metadata (captions, media type).
2.  Extracts Content Features (8-dim) using the TranscriptFeatureExtractor or Caption analysis.
3.  Pulls real city-level insights from the Instagram Insights API.
4.  Formats and stores a "Hybrid Training Sample" (Real Data + Content DNA).
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import requests
import asyncio

from backend.app.services.transcript_feature_extractor import TranscriptFeatureExtractor
from backend.app.db.base import SessionLocal
from backend.app.db.models import Campaign, InsightSnapshot
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class InstagramGNNBridge:
    """
    Connects real Instagram performance metrics to the GNN training pipeline.
    """

    def __init__(self, access_token: str, account_id: str):
        self.access_token = access_token
        self.account_id = account_id
        self.extractor = TranscriptFeatureExtractor()

    # ─── CORE WORKFLOW ───────────────────────────────────────────────────

    async def ingest_post_to_gnn(
        self, 
        post_id: str, 
        category: str = "General", 
        campaign_uid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        The full bridge: Fetch -> Extract -> Store -> Format for GNN.
        """
        db = SessionLocal()
        try:
            # 1. Fetch Post Metadata
            logger.info(f"Bridgeing post {post_id} to GNN...")
            post_meta = self._fetch_ig_metadata(post_id)
            if not post_meta:
                return {"status": "error", "message": "Post metadata not found"}

            # 2. Extract Content Features
            # For Instagram, we analyze the Caption and Hashtags as the "signal" 
            # if no direct YouTube transcript is available.
            caption = post_meta.get("caption", "")
            media_type = post_meta.get("media_type", "IMAGE")
            
            # Use extractor logic on caption if it's a short text, or try to find a link
            content_features = self._extract_features_optimized(caption, category)
            
            # 3. Pull Real City Insights
            city_insights = self._fetch_city_insights(post_id)
            if not city_insights:
                logger.warning(f"No city insights available yet for {post_id} (post may be too fresh)")
            
            # 4. Update Database
            campaign = self._get_or_create_campaign(db, post_id, category, content_features, campaign_uid)
            self._store_insights(db, campaign.campaign_id, city_insights, content_features)

            return {
                "status": "success",
                "campaign_id": campaign.campaign_id,
                "category": category,
                "content_features": content_features,
                "cities_hit": len(city_insights)
            }

        finally:
            db.close()

    # ─── EXTRACTION LOGIC ────────────────────────────────────────────────

    def _extract_features_optimized(self, text: str, category: str) -> List[float]:
        """
        Adapts the TranscriptFeatureExtractor to work on Instagram captions.
        """
        # Since captions are shorter, we wrap them as a single segment for the extractor
        segments = [{"text": text, "start": 0, "duration": 30}]
        return self.extractor._compute_features(segments, category)

    # ─── API INTERACTION ────────────────────────────────────────────────

    def _fetch_ig_metadata(self, post_id: str) -> Dict:
        """Fetch basic post info from Instagram"""
        url = f"https://graph.facebook.com/v18.0/{post_id}"
        params = {
            "access_token": self.access_token,
            "fields": "caption,media_type,timestamp,permalink"
        }
        resp = requests.get(url, params=params)
        return resp.json() if resp.status_code == 200 else {}

    def _fetch_city_insights(self, post_id: str) -> List[Dict]:
        """Fetch city-level breakdown from IG Insights API"""
        url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
        params = {
            "access_token": self.access_token,
            "metric": "reach",  # Primary metric for GNN spread
            "breakdown": "city"
        }
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        city_records = []
        if 'data' in data and data['data']:
            metric_data = data['data'][0]
            values = metric_data.get('values', [])
            for val in values:
                breakdown = val.get('breakdown', {})
                if 'city' in breakdown:
                    city_records.append({
                        "city": breakdown['city'].get('name', 'Unknown'),
                        "reach": val.get('value', 0),
                        "timestamp": datetime.now()
                    })
        return city_records

    # ─── STORAGE ────────────────────────────────────────────────────────

    def _get_or_create_campaign(
        self, 
        db, 
        post_id: str, 
        category: str, 
        features: List[float],
        uid: Optional[str]
    ) -> Campaign:
        # Check if exists
        campaign = db.query(Campaign).filter(Campaign.post_id == post_id).first()
        if not campaign:
            cid = uid or f"ig_{post_id[-8:]}"
            campaign = Campaign(
                campaign_id=cid,
                post_id=post_id,
                platform="instagram",
                category=category,
                content_features=features
            )
            db.add(campaign)
            db.commit()
            db.refresh(campaign)
        else:
            # Update
            campaign.category = category
            campaign.content_features = features
            db.commit()
        return campaign

    def _store_insights(self, db, campaign_id: str, city_data: List[Dict], features: List[float]):
        from generate_synthetic_gnn_data import calculate_content_boost
        boost = calculate_content_boost(features)

        for record in city_data:
            # Upsert insight record
            snap = db.query(InsightSnapshot).filter(
                InsightSnapshot.campaign_id == campaign_id,
                InsightSnapshot.city == record['city']
            ).first()
            
            if not snap:
                snap = InsightSnapshot(
                    campaign_id=campaign_id,
                    city=record['city'],
                    reach=record['reach'],
                    content_boost=boost,
                    timestamp=record['timestamp']
                )
                db.add(snap)
            else:
                snap.reach = record['reach']
                snap.content_boost = boost
            
        db.commit()

    # ─── EXPORT FOR GNN ──────────────────────────────────────────────────

    def export_hybrid_dataset(self, output_file: str = "gnn_hybrid_training_data.json"):
        """
        Merges Real Instagram Data records with the existing Synthetic dataset.
        This provides "High Stability" (Synthetic) + "Ground Truth" (Real).
        """
        db = SessionLocal()
        try:
            # 1. Load Synthetic Data
            syn_path = "gnn_synthetic_multicategory_data.json"
            if os.path.exists(syn_path):
                with open(syn_path, 'r') as f:
                    final_data = json.load(f)
            else:
                final_data = []

            # 2. Get Real Data from Database
            campaigns = db.query(Campaign).filter(Campaign.content_features != None).all()
            for kamp in campaigns:
                snaps = db.query(InsightSnapshot).filter(InsightSnapshot.campaign_id == kamp.campaign_id).all()
                if not snaps: continue

                nodes_hit = [s.city for s in snaps]
                # Format to match GNN schema
                real_sample = {
                    "campaign_id": kamp.campaign_id,
                    "category": kamp.category,
                    "start_city": nodes_hit[0] if nodes_hit else "Mumbai",
                    "content_features": kamp.content_features,
                    "content_boost": snaps[0].content_boost if snaps else 1.0,
                    "nodes_hit": nodes_hit,
                    "edges": [], # Can be reconstructed from timestamps if needed
                    "is_real": True
                }
                final_data.append(real_sample)

            # 3. Save
            with open(output_file, 'w') as f:
                json.dump(final_data, f, indent=2, default=str)
            
            logger.info(f"Hybrid dataset saved: {len(final_data)} samples total.")
            return final_data

        finally:
            db.close()
import os
