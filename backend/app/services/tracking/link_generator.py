"""
Tracking Link Generator
=======================

Generates unique tracking links for campaigns.
"""

import secrets
from typing import Optional
from backend.app.core.config import settings


class LinkGenerator:
    """Generates tracking links for campaigns."""
    
    @staticmethod
    def generate_campaign_id(prefix: str = "ig") -> str:
        """Generate a unique campaign ID."""
        random_part = secrets.token_hex(4)  # 8 characters
        return f"{prefix}_{random_part}"
    
    @staticmethod
    def generate_tracking_link(campaign_id: str, domain: Optional[str] = None) -> str:
        """Generate the tracking link URL."""
        if domain is None:
            domain = getattr(settings, 'TRACKING_DOMAIN', 'https://yourdomain.com')
        return f"{domain}/p/{campaign_id}"