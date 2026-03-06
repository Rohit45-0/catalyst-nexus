"""
Instagram OAuth Service
=======================

Handles the intricate dance of Facebook Login -> Access Token -> Instagram Business Account.
"""

import httpx
from urllib.parse import urlencode
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from backend.app.db.models import User
import logging

logger = logging.getLogger(__name__)

class InstagramOAuthService:
    """Service to handle Instagram (Facebook) OAuth flow."""
    
    FACEBOOK_GRAPH_URL = "https://graph.facebook.com/v19.0"
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.app_id = settings.FACEBOOK_APP_ID
        self.app_secret = settings.FACEBOOK_APP_SECRET
        # Redirect URI must match exactly what is in Facebook App Settings
        self.redirect_uri = f"{settings.API_BASE_URL}/api/v1/auth/instagram/callback"
        
    def get_login_url(self, state: str) -> str:
        """
        Generate the Facebook Login URL.
        
        Args:
            state: A random string to prevent CSRF attacks.
        """
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "response_type": "code",
            "scope": "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement,public_profile"
        }
        return f"https://www.facebook.com/v19.0/dialog/oauth?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange the authorization code for a long-lived access token.
        """
        async with httpx.AsyncClient() as client:
            # 1. Exchange code for short-lived token
            token_url = f"{self.FACEBOOK_GRAPH_URL}/oauth/access_token"
            params = {
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "redirect_uri": self.redirect_uri,
                "code": code
            }
            response = await client.get(token_url, params=params)
            if response.status_code != 200:
                logger.error(f"Failed to get access token: {response.text}")
                raise Exception("Failed to retrieve access token from Facebook")
            
            data = response.json()
            short_lived_token = data["access_token"]
            
            # 2. Exchange short-lived token for long-lived token (60 days)
            long_token_url = f"{self.FACEBOOK_GRAPH_URL}/oauth/access_token"
            long_params = {
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": short_lived_token
            }
            long_response = await client.get(long_token_url, params=long_params)
            
            if long_response.status_code == 200:
                return long_response.json()  # Return the long-lived token data
            else:
                # Fallback to short-lived if exchange fails (rare)
                return data

    async def get_instagram_business_account(self, access_token: str) -> Optional[Dict[str, str]]:
        """
        Find the user's connected Instagram Business Account ID.
        """
        async with httpx.AsyncClient() as client:
            # 1. Get user's pages
            pages_url = f"{self.FACEBOOK_GRAPH_URL}/me/accounts"
            response = await client.get(pages_url, params={"access_token": access_token})
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch pages: {response.text}")
                return None
                
            pages_data = response.json()
            
            # 2. Iterate through pages to find one with an IG Business Account
            for page in pages_data.get("data", []):
                page_id = page["id"]
                page_token = page["access_token"] # Page-scoped token
                
                # Check for connected IG account
                ig_url = f"{self.FACEBOOK_GRAPH_URL}/{page_id}"
                ig_response = await client.get(ig_url, params={
                    "fields": "instagram_business_account",
                    "access_token": page_token
                })
                
                ig_data = ig_response.json()
                if "instagram_business_account" in ig_data:
                    return {
                        "instagram_id": ig_data["instagram_business_account"]["id"],
                        "page_id": page_id,
                        "page_name": page["name"],
                        "page_access_token": page_token # Save this if possible, it's better for publishing
                    }
            
            return None

    async def connect_user_account(self, user_id: str, code: str) -> Dict[str, Any]:
        """
        Main orchestrator: Code -> Token -> Find IG Account -> Save to DB.
        """
        # 1. Get Token
        token_data = await self.exchange_code_for_token(code)
        access_token = token_data["access_token"]
        
        # 2. Find Instagram Business Account
        ig_account = await self.get_instagram_business_account(access_token)
        
        if not ig_account:
            raise Exception("No Instagram Business account found linked to your Facebook Pages.")
            
        # 3. Update User in DB
        # Note: We are using a simple string update here, but normally you'd use the ORM session passed in __init__
        # Since this method is async and we need to commit, we'll do it in the API endpoint handler
        
        return {
            "access_token": access_token, # User long-lived token
            "page_token": ig_account["page_access_token"], # Page token (ideal for publishing)
            "instagram_id": ig_account["instagram_id"],
            "page_name": ig_account["page_name"]
        }
