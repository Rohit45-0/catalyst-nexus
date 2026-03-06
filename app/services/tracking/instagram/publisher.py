"""
Instagram Publisher
===================

Handles publishing to Instagram and storing post mappings.
"""

from typing import Optional
import requests
from backend.app.core.config import settings


class InstagramPublisher:
    """Publishes content to Instagram via Graph API."""
    
    def __init__(self):
        self.access_token = getattr(settings, 'INSTAGRAM_ACCESS_TOKEN', None)
        self.account_id = getattr(settings, 'INSTAGRAM_ACCOUNT_ID', None)
    
    def publish_post(self, media_url: str, caption: str) -> Optional[str]:
        """Publish media to Instagram and return post ID."""
        if not self.access_token or not self.account_id:
            raise ValueError("Instagram credentials not configured")
        
        url = f"https://graph.facebook.com/v18.0/{self.account_id}/media"
        params = {
            'access_token': self.access_token,
            'image_url': media_url,  # Assuming image for now
            'caption': caption
        }
        
        response = requests.post(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get('id')
        return None
    
    def get_post_insights(self, post_id: str) -> dict:
        """Get insights for a post."""
        url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
        params = {
            'access_token': self.access_token,
            'metric': 'reach,impressions,engagement,shares,saves'
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return {}
