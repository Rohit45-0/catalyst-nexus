"""
Assistant Chat API
==================
POST /api/v1/assistant/chat

Modes:
  - web_search=false (default): Pure GPT conversation with history
  - web_search=true:  Brave Search → inject results as context → GPT answers

The chat history is passed by the client (last N messages) so the model
has memory of the conversation without any server-side session storage.
"""

import json
import logging
from typing import Annotated, Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.security import get_current_user
from backend.app.db.models import User
from backend.app.db.base import get_db
from sqlalchemy.orm import Session
from backend.app.services.search_service import SearchService, get_search_service
from backend.app.services.rag_service import RagService, get_rag_service

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str          # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: List[ChatMessage] = Field(default_factory=list, description="Last N turns of conversation")
    web_search: bool = Field(False, description="If true, search the web first and use it as context")
    max_history: int = Field(12, ge=1, le=40, description="How many history messages to send to GPT")


class SearchResult(BaseModel):
    title: str = ""
    link: str = ""
    snippet: str = ""


class ChatResponse(BaseModel):
    reply: str
    web_results: List[SearchResult] = []
    web_search_used: bool = False
    rag_used: bool = False
    rag_source: str = "none"  # "pgvector", "db_fallback", "none"


# ─── Helpers ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Catalyst Nexus AI — a creative marketing and product strategy assistant.
You help brands with:
- Campaign ideas, ad copy, social media content
- Market analysis and competitor insights
- Product positioning and branding strategy
- Content creation across all formats (reels, blogs, posters, tweets)

CRITICAL RULES:
1. If the user asks about campaigns they created, ONLY reference data from the "Past Campaign Knowledge" section below.
2. If there is NO past campaign data provided, honestly say: "I don't have any campaign data on file for you yet. Generate a campaign first and I'll be able to reference it."
3. NEVER invent or hallucinate campaign details. Only discuss campaigns that appear in the provided knowledge context.
4. If the user asks you to create or generate a video, respond with: [GENERATE_VIDEO] <detailed visual prompt for SORA-2 in one line>
5. If the user asks you to create or generate an image/poster, respond with: [GENERATE_IMAGE] <detailed visual prompt for DALL-E in one line>

Be concise, tactical, and creative. When web search results are provided,
use them to give accurate, up-to-date answers. Always attribute information
to the sources when using web search context.

If the user just says hi or asks a casual question, respond naturally and warmly."""


async def _gpt_chat(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> str:
    """Call Azure OpenAI GPT with the given messages list."""
    if not settings.AZURE_OPENAI_API_KEY or not settings.AZURE_OPENAI_ENDPOINT:
        return "⚠️ AI service not configured. Please set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT."

    url = (
        f"{settings.AZURE_OPENAI_ENDPOINT.rstrip('/')}"
        f"/openai/deployments/{settings.AZURE_DEPLOYMENT_NAME}"
        f"/chat/completions?api-version=2024-02-15-preview"
    )
    payload = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    headers = {"Content-Type": "application/json", "api-key": settings.AZURE_OPENAI_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.error(f"GPT chat failed: {exc}")
        return "I'm having trouble connecting to the AI service right now. Please try again in a moment."


def _build_web_context_block(results: List[dict]) -> str:
    """Format search results into a readable context block for the system prompt."""
    if not results:
        return ""
    lines = ["Here are relevant web search results for context:\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        lines.append(f"   Source: {r['link']}")
        lines.append(f"   {r['snippet']}")
        lines.append("")
    lines.append("Use the above search results to provide an accurate, well-informed answer.")
    return "\n".join(lines)


def _build_rag_context_block(chunks) -> str:
    """Format retrieved RAG chunks into a system prompt block."""
    if not chunks:
        return ""
    lines = ["Here is relevant knowledge from past campaigns and brand memory:\n"]
    for i, c in enumerate(chunks, 1):
        lines.append(f"- [{c.category.replace('_', ' ').title()}]: {c.content}")
    lines.append("\nUse this knowledge to personalize your answer and align with brand history.")
    return "\n".join(lines)


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Catalyst Nexus AI Chat (with optional web search context)",
)
async def assistant_chat(
    body: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    search_svc: SearchService = Depends(get_search_service),
    db: Session = Depends(get_db),
):
    """
    Pure GPT conversation by default.
    When web_search=true, Brave fetches live results → injected as context → GPT answers grounded in real data.
    Chat history is preserved via client-side messages passed in `history`.
    """
    web_results: List[dict] = []

    # ── Step 1: Web search (only if requested) ────────────────────────────────
    if body.web_search:
        # Reuse existing SearchService (Brave → Serper → DuckDuckGo fallback)
        raw = await search_svc.search(body.message, max_results=5)
        web_results = [
            {"title": r.get("title", ""), "link": r.get("link", ""), "snippet": r.get("snippet", "")}
            for r in raw if r.get("link")
        ]

    # ── Step 2: RAG Retrieval (Use Memory) ──────────────────────────────────
    # Check if we have any relevant past knowledge
    rag_chunks = []
    rag_source = "none"
    try:
        rag = get_rag_service(db)
        rag_chunks = await rag.search(body.message, user_id=current_user.id, limit=5)
        if rag_chunks:
            # Detect which source was used
            rag_source = "pgvector" if rag._check_pgvector_available() else "db_fallback"
            logger.info(f"✅ RAG returned {len(rag_chunks)} chunks via {rag_source}")
        else:
            logger.info(f"ℹ️ RAG search returned 0 results for user {current_user.id}")
    except Exception as e:
        logger.warning(f"RAG search failed: {e}")

    # ── Step 3: Build GPT messages array ─────────────────────────────────────
    system_content = SYSTEM_PROMPT
    
    # Inject RAG Memory
    if rag_chunks:
        system_content += "\n\n" + _build_rag_context_block(rag_chunks)
    else:
        system_content += "\n\nPast Campaign Knowledge: NONE — the user has not generated any campaigns yet, or no relevant data was found."
        
    # Inject Web Search (Live Data)
    if web_results:
        system_content += "\n\n" + _build_web_context_block(web_results)

    gpt_messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_content}
    ]

    # Append conversation history (trim to max_history to control tokens)
    for msg in body.history[-body.max_history:]:
        gpt_messages.append({"role": msg.role, "content": msg.content})

    # Append the new user message
    gpt_messages.append({"role": "user", "content": body.message})

    # ── Step 3: Call GPT ──────────────────────────────────────────────────────
    reply = await _gpt_chat(gpt_messages)

    # ── Step 4: Handle Media Generation Commands ──────────────────────────────
    import re
    from backend.app.db.models import GeneratedCampaign
    from backend.app.agents.neural_render import get_render_agent, RenderRequest, RenderQuality, RenderBackend

    # Check for Video Generation Command
    video_match = re.search(r"\[GENERATE_VIDEO\]\s*(.+)", reply, re.IGNORECASE)
    if video_match:
        prompt = video_match.group(1).strip()
        try:
            render_agent = get_render_agent()
            render_result = await render_agent.render_video(
                RenderRequest(
                    prompt=prompt,
                    duration_seconds=5.0,
                    quality=RenderQuality.STANDARD,
                    backend=RenderBackend.SORA_2
                )
            )
            if render_result.status == "completed" and render_result.output_path:
                from backend.app.api.v1.market_intel import _relative_project_path, _download_url
                import uuid
                from pathlib import Path
                
                local_path = Path(render_result.output_path).resolve()
                download_url = _download_url(local_path)
                
                # Append to reply so frontend renders it
                reply += f"\n\n[video]({download_url})"
                
                # Optionally save a minimal campaign entry so it appears in Content Library
                try:
                    gc = GeneratedCampaign(
                        user_id=current_user.id,
                        project_id=None,
                        product_name="Assistant Generation",
                        campaign_strategy="Direct Assistant Generation",
                        poster_ideas=[],
                        poster_assets=[
                            {"name": local_path.name, "download_url": download_url, "asset_type": "video"}
                        ],
                    )
                    db.add(gc)
                    db.commit()
                except Exception as e:
                    logger.warning(f"Could not save standalone video to library: {e}")
        except Exception as e:
            reply += f"\n\n⚠️ Failed to generate video: {str(e)}"

    # Check for Image Generation Command
    image_match = re.search(r"\[GENERATE_IMAGE\]\s*(.+)", reply, re.IGNORECASE)
    if image_match:
        prompt = image_match.group(1).strip()
        try:
            render_agent = get_render_agent()
            render_result = await render_agent.render_image(
                RenderRequest(
                    prompt=prompt,
                    width=1024,
                    height=1024,
                    quality=RenderQuality.STANDARD,
                    backend=RenderBackend.DALLE_3
                )
            )
            if render_result.status == "completed" and render_result.output_path:
                from backend.app.api.v1.market_intel import _relative_project_path, _download_url
                from pathlib import Path
                
                local_path = Path(render_result.output_path).resolve()
                download_url = _download_url(local_path)
                
                # Append to reply
                reply += f"\n\n![Generated Image]({download_url})"
                
                # Save to Content Library
                try:
                    gc = GeneratedCampaign(
                        user_id=current_user.id,
                        project_id=None,
                        product_name="Assistant Generation",
                        campaign_strategy="Direct Assistant Generation",
                        poster_assets=[
                            {"name": local_path.name, "download_url": download_url, "asset_type": "poster"}
                        ],
                    )
                    db.add(gc)
                    db.commit()
                except Exception as e:
                    logger.warning(f"Could not save standalone image to library: {e}")
        except Exception as e:
            reply += f"\n\n⚠️ Failed to generate image: {str(e)}"

    # ── Step 5: Store chat turn for future RAG retrieval ───────────────────
    try:
        rag = get_rag_service(db)
        await rag.store_chat_turn(current_user.id, body.message, reply)
    except Exception as e:
        logger.warning(f"Failed to store chat turn in RAG: {e}")

    return ChatResponse(
        reply=reply,
        web_results=[SearchResult(**r) for r in web_results],
        web_search_used=bool(web_results),
        rag_used=bool(rag_chunks),
        rag_source=rag_source,
    )
