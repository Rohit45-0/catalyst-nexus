from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
import structlog
from typing import Optional

from backend.app.core.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.get("/webhook")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    """
    Endpoint required by Meta to verify the Webhook URL.
    Meta will send a GET request here when you first configure it in the portal.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("✅ Verified Meta WhatsApp Webhook successfully!")
        return int(hub_challenge)  # Must return the challenge integer
    
    logger.warning("Failed Meta WhatsApp Webhook verification: Token mismatch")
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@router.post("/webhook")
async def handle_whatsapp_message(request: Request, background_tasks: BackgroundTasks):
    """
    Main webhook listener that Meta posts to when a user messages the bot.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Fast return to Meta to acknowledge receipt (Meta expects 200 OK within 3 seconds)
    # We will process the actual message asynchronously
    logger.info("Received WhatsApp Payload from Meta", payload=payload)
    
    # Process message logic would go here:
    # 1. Parse payload to get 'from' number and 'text.body'
    return {"status": "ok"}
