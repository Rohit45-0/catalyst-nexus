"""Instagram Graph API adapter for publishing + analytics ingestion."""

from typing import Optional, List, Dict, Any
import requests
from backend.app.core.config import settings


class InstagramPublisher:
    """Publishes content to Instagram via Graph API."""
    
    def __init__(self):
        self.access_token = getattr(settings, 'INSTAGRAM_ACCESS_TOKEN', None)
        self.account_id = getattr(settings, 'INSTAGRAM_ACCOUNT_ID', None)
    
    def publish_media_post(self, media_url: str, caption: str) -> Optional[str]:
        """Publish media to Instagram and return post ID."""
        if not self.access_token or not self.account_id:
            raise ValueError("Instagram credentials not configured")
        
        # Step 1: Create media container
        url = f"https://graph.facebook.com/v18.0/{self.account_id}/media"
        params = {
            'access_token': self.access_token,
            'image_url': media_url,
            'caption': caption
        }
        
        response = requests.post(url, params=params)
        if response.status_code != 200:
            err_msg = response.json().get('error', {}).get('message', str(response.text))
            raise ValueError(f"Meta API Error: {err_msg}")
        
        data = response.json()
        container_id = data.get('id')
        if not container_id:
            return None
        
        # Step 2: Publish the media
        publish_url = f"https://graph.facebook.com/v18.0/{self.account_id}/media_publish"
        publish_params = {
            'access_token': self.access_token,
            'creation_id': container_id
        }
        
        publish_response = requests.post(publish_url, params=publish_params)
        if publish_response.status_code == 200:
            publish_data = publish_response.json()
            return publish_data.get('id')  # This is the post ID
        return None
    
    def publish_text_post(self, message: str) -> Optional[str]:
        """Publish a text-only post to Instagram."""
        if not self.access_token or not self.account_id:
            raise ValueError("Instagram credentials not configured")
        
        url = f"https://graph.facebook.com/v18.0/{self.account_id}/feed"
        params = {
            'access_token': self.access_token,
            'message': message
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

    def get_hashtag_id(self, hashtag: str) -> Optional[str]:
        """Resolve hashtag text to IG hashtag ID via Graph API."""
        if not self.access_token or not self.account_id:
            raise ValueError("Instagram credentials not configured")

        url = "https://graph.facebook.com/v18.0/ig_hashtag_search"
        params = {
            "access_token": self.access_token,
            "user_id": self.account_id,
            "q": hashtag.lstrip("#"),
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return None

        data = response.json().get("data", [])
        return data[0].get("id") if data else None

    def get_recent_hashtag_media(self, hashtag_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch recent media for hashtag and keep only Reel/video-leaning fields."""
        if not self.access_token or not self.account_id:
            raise ValueError("Instagram credentials not configured")

        url = f"https://graph.facebook.com/v18.0/{hashtag_id}/recent_media"
        params = {
            "access_token": self.access_token,
            "user_id": self.account_id,
            "limit": max(5, min(limit, 50)),
            "fields": "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count",
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return []

        media = response.json().get("data", [])
        reels_only = [
            item for item in media
            if str(item.get("media_type", "")).upper() in {"VIDEO", "REEL", "CAROUSEL_ALBUM"}
        ]
        return reels_only