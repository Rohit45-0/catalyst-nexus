"""
Publishing Node for Catalyst Nexus Orchestrator
===============================================

Handles publishing of generated videos to social media platforms.
"""

import logging
from typing import Dict, Any
from datetime import datetime
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class PublishNode:
    """
    Publishing Stage: Distribute content to social media platforms.
    
    Features:
    - Multi-platform publishing (Instagram, LinkedIn, etc.)
    - Automatic campaign creation
    - Tracking link generation
    - Analytics integration
    """
    
    def __init__(self):
        """Initialize the publish node."""
        self.enabled = True
        try:
            from backend.app.services.publishing_service import PublishingService
            from backend.app.db.base import get_db
            self._PublishingService = PublishingService
        except ImportError as e:
            logger.warning(f"Publishing service not available: {e}")
            self.enabled = False
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute publishing stage."""
        logger.info(f"📤 Publish Stage - Job: {state['job_id']}")
        
        state["status"] = "publishing"
        state["current_stage"] = "publish"
        state["progress_percent"] = 95.0
        state["updated_at"] = datetime.utcnow().isoformat()
        state["stage_messages"] = [f"[{state['updated_at']}] Starting publication..."]
        
        try:
            # Check if auto-publish is enabled
            auto_publish = state.get("auto_publish", False)
            
            if not auto_publish:
                logger.info("Auto-publish disabled, skipping publication")
                state["stage_messages"] = [
                    f"[{datetime.utcnow().isoformat()}] ⏭️ Auto-publish disabled, manual publishing required"
                ]
                state["progress_percent"] = 98.0
                return state
            
            # Check if publishing service is available
            if not self.enabled:
                logger.warning("Publishing service not available")
                state["stage_messages"] = [
                    f"[{datetime.utcnow().isoformat()}] ⚠️ Publishing service not available"
                ]
                state["progress_percent"] = 98.0
                return state
            
            # Get video URL
            video_url = state.get("video_url")
            if not video_url:
                logger.warning("No video URL found, skipping publication")
                state["stage_messages"] = [
                    f"[{datetime.utcnow().isoformat()}] ⚠️ No video URL available for publishing"
                ]
                state["progress_percent"] = 98.0
                return state
            
            # Get platforms and caption
            platforms = state.get("publish_to_platforms", ["instagram"])
            caption = state.get("publish_caption") or self._generate_default_caption(state)
            
            # Import DB session (this should be passed properly in production)
            from backend.app.db.base import SessionLocal
            db = SessionLocal()
            
            try:
                publishing_service = self._PublishingService(db)
                
                # Publish to platforms
                publish_results = {}
                for platform in platforms:
                    if platform.lower() == "instagram":
                        result = await publishing_service.publish_to_instagram(
                            media_url=video_url,
                            caption=caption,
                            user_id=1  # TODO: Get from state or context
                        )
                        publish_results[platform] = result
                        
                        # Store campaign info in state
                        if result.get("success"):
                            state["campaign_id"] = result.get("campaign_id")
                            state["tracking_link"] = result.get("tracking_link")
                
                state["publish_results"] = publish_results
                
                # Check if any platform succeeded
                success_count = sum(1 for r in publish_results.values() if r.get("success"))
                
                if success_count > 0:
                    state["stage_messages"] = [
                        f"[{datetime.utcnow().isoformat()}] ✅ Published to {success_count}/{len(platforms)} platform(s)"
                    ]
                else:
                    state["errors"] = [f"Failed to publish to any platform"]
                
            finally:
                db.close()
            
            state["progress_percent"] = 98.0
            
        except Exception as e:
            logger.error(f"Publishing failed: {e}")
            state["errors"] = [f"Publish stage failed: {str(e)}"]
            # Don't stop the workflow, just log the error
        
        return state
    
    def _generate_default_caption(self, state: Dict[str, Any]) -> str:
        """Generate a default caption based on product info."""
        product_name = state.get("product_name", "Product")
        brand_guidelines = state.get("brand_guidelines", {})
        brand_name = brand_guidelines.get("brand_name", "")
        
        caption = f"Discover the {product_name}"
        if brand_name:
            caption += f" by {brand_name}"
        
        caption += " ✨\n\n#product #innovation #quality"
        
        return caption


def route_after_publish(state: Dict[str, Any]) -> str:
    """Route after publishing stage."""
    return "finalize"
