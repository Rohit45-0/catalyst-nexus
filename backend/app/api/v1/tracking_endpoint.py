"""
Click Tracking Endpoint - Capture REAL Clicks
==============================================

This endpoint logs REAL clicks when users click your tracking link.
Add this to your FastAPI app to capture real click data.
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from datetime import datetime
import httpx

from backend.app.db.base import get_db
from backend.app.db.models import ClickEvent

router = APIRouter()


@router.get("/p/{campaign_id}")
async def track_click(campaign_id: str, request: Request):
    """
    Track click on campaign link.
    
    When someone clicks: https://yourdomain.com/p/laptop_tracked_xxx
    This endpoint:
    1. Gets their IP address
    2. Converts IP → City/Country (using IP geolocation API)
    3. Logs: campaign_id, city, country, timestamp
    4. Deletes IP immediately (privacy-safe)
    5. Redirects user to your landing page
    """
    
    # Get user's IP address
    client_ip = request.client.host
    
    # For local/development, use a different method
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    # Convert IP to City/Country using free IP geolocation API
    city = "Unknown"
    country = "Unknown"
    
    try:
        # Using free ip-api.com service
        if client_ip and client_ip not in ["127.0.0.1", "localhost"]:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://ip-api.com/json/{client_ip}",
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    city = data.get("city", "Unknown")
                    country = data.get("country", "Unknown")
        else:
            # Local testing fallback
            city = "Local"
            country = "Development"
    
    except Exception as e:
        print(f"Geolocation failed: {e}")
        city = "Unknown"
        country = "Unknown"
    
    # Log click event (NO IP stored - privacy-safe!)
    db = next(get_db())
    
    try:
        click_event = ClickEvent(
            campaign_id=campaign_id,
            city=city,
            country=country,
            # timestamp is auto-set by database
        )
        db.add(click_event)
        db.commit()
        
        print(f"✅ Click logged: {campaign_id} from {city}, {country}")
    
    except Exception as e:
        print(f"Failed to log click: {e}")
        db.rollback()
    
    finally:
        db.close()
    
    # Redirect to your landing page or product page
    # Change this URL to wherever you want users to land
    return RedirectResponse(
        url="https://www.instagram.com/itsfunyyyyyyyy/",
        status_code=302
    )


# Optional: Add to main.py
"""
To enable this in your FastAPI app, add to main.py:

from backend.app.api.v1 import tracking_endpoint

app.include_router(
    tracking_endpoint.router,
    tags=["tracking"]
)
"""
