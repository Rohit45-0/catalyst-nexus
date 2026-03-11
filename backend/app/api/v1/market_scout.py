"""
Market Scout API
================
Step 2 of the Catalyst Nexus workflow.

POST /market-scout/analyze
  Accepts: product_name, category, competitor_urls (optional), keywords
  Pipeline:
    1. Firecrawl → web search for competitor content + trends
    2. Firecrawl → optionally scrape competitor URLs for full content
    3. GPT-4o → gap analysis (top questions, complaints, viral hooks, opportunity)
  Returns: structured gap analysis + top competitor insights

GET /market-scout/trending?category=
  Quick Firecrawl-powered trend snapshot without LLM (fast/cheap).
"""

import asyncio
import json
import logging
import re
from typing import Annotated, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.security import get_current_user
from backend.app.db.models import User

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ScoutRequest(BaseModel):
    product_name: str = Field(..., description="Your product name")
    category: str = Field(..., description="Product category / niche")
    keywords: Optional[List[str]] = Field(None, description="Extra keywords to search")
    competitor_urls: Optional[List[str]] = Field(None, description="URLs to scrape (1–5)")
    region: str = Field("IN", description="2-char region code")


class BotScoutRequest(BaseModel):
    user_id: str
    product_name: str
    category: str
    phone_number: str
    phone_number_id: str


class CompetitorResult(BaseModel):
    url: str
    title: str
    description: str
    source: str           # "firecrawl_search" | "firecrawl_scrape"
    key_points: List[str]


class GapAnalysis(BaseModel):
    top_questions: List[str]
    complaints: List[str]
    viral_hooks: List[str]
    opportunity_gap: str
    recommended_angles: List[str]


class ContentTrend(BaseModel):
    title: str
    url: str
    source: str
    relevance_snippet: str


class ScoutResponse(BaseModel):
    product_name: str
    category: str
    competitor_results: List[CompetitorResult]
    trending_content: List[ContentTrend]
    gap_analysis: GapAnalysis
    firecrawl_credits_used: int
    data_sources: List[str]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_firecrawl():
    """Return a Firecrawl client or None if not configured."""
    if not settings.FIRECRAWL_API_KEY:
        return None
    try:
        from firecrawl import FirecrawlApp
        return FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)
    except Exception as exc:
        logger.warning(f"Could not init Firecrawl: {exc}")
        return None


def _firecrawl_search(client, query: str, limit: int = 5) -> list:
    """Sync Firecrawl search (run in thread pool)."""
    try:
        results = client.search(query, params={"limit": limit})
        data = results if isinstance(results, list) else getattr(results, "data", [])
        out = []
        for item in data:
            if isinstance(item, dict):
                out.append(item)
            else:
                out.append({
                    "url": getattr(item, "url", ""),
                    "title": getattr(item, "title", ""),
                    "description": getattr(item, "description", ""),
                    "markdown": getattr(item, "markdown", ""),
                })
        return out
    except Exception as exc:
        logger.warning(f"Firecrawl search failed: {exc}")
        return []


def _firecrawl_scrape(client, url: str) -> dict:
    """Sync Firecrawl scrape (run in thread pool)."""
    try:
        result = client.scrape_url(url, formats=["markdown", "metadata"])
        return {
            "url": url,
            "markdown": result.markdown if hasattr(result, "markdown") else "",
            "metadata": result.metadata if hasattr(result, "metadata") else {},
        }
    except Exception as exc:
        logger.warning(f"Firecrawl scrape failed for {url}: {exc}")
        return {"url": url, "markdown": "", "metadata": {}}


GAP_ANALYSIS_SYSTEM = """You are a Market Intelligence Analyst for digital products and brands.
You analyze competitor content and web trends to find strategic content gaps.

Return ONLY valid JSON with exactly this structure:
{
    "top_questions": ["question audiences are asking but nobody answers", ...],
    "complaints": ["frustrations or pain points visible in comments/reviews", ...],
    "viral_hooks": ["specific headline or hook patterns that drive high engagement", ...],
    "opportunity_gap": "1-2 sentence description of the biggest content opportunity gap",
    "recommended_angles": ["specific content angle #1 the brand should create", ...]
}

Be specific, actionable, and data-driven. Each list should have 3-5 items."""


async def _run_gap_analysis(
    product_name: str,
    category: str,
    competitor_texts: List[str],
) -> dict:
    """Call Azure OpenAI to analyze competitor content and find gaps."""
    if not settings.AZURE_OPENAI_API_KEY or not settings.AZURE_OPENAI_ENDPOINT:
        return {
            "top_questions": [f"How does {product_name} compare to alternatives?",
                              f"What are the best {category} products in 2025?"],
            "complaints": ["Pricing transparency missing", "Limited review content"],
            "viral_hooks": ["'I tested every {category} product' format",
                            "Before/after transformation content"],
            "opportunity_gap": f"There is a gap in authentic, educational {category} content that directly addresses common buyer hesitations around products like {product_name}.",
            "recommended_angles": [f"Create 'Why {product_name}' educational series",
                                   f"Address top 3 objections head-on in first 5 seconds"],
        }

    context = "\n\n---\n\n".join(competitor_texts[:8])[:6000]  # token budget
    user_msg = (
        f"Product: {product_name}\nCategory: {category}\n\n"
        f"Competitor content collected from the web:\n\n{context}\n\n"
        "Analyze the above to find content gaps and opportunities."
    )

    url = (
        f"{settings.AZURE_OPENAI_ENDPOINT.rstrip('/')}"
        f"/openai/deployments/{settings.AZURE_DEPLOYMENT_NAME}"
        f"/chat/completions?api-version=2024-02-15-preview"
    )
    payload = {
        "messages": [
            {"role": "system", "content": GAP_ANALYSIS_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 1200,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }
    headers = {"Content-Type": "application/json", "api-key": settings.AZURE_OPENAI_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            return json.loads(raw)
    except Exception as exc:
        logger.error(f"Gap analysis LLM failed: {exc}")
        return {
            "top_questions": [f"What makes {product_name} different?"],
            "complaints": ["Not enough comparison content available"],
            "viral_hooks": ["'Honest review' format outperforms polished ads"],
            "opportunity_gap": f"Educational and comparison content for {category} is underserved.",
            "recommended_angles": [f"Build trust-first content for {product_name} positioning"],
        }


def _extract_key_points(markdown: str, max_points: int = 4) -> List[str]:
    """Pull up to max_points bullet-worthy sentences from markdown."""
    sentences = re.split(r"(?<=[.!?])\s+", (markdown or "").replace("\n", " "))
    good = [s.strip() for s in sentences if 20 < len(s.strip()) < 200]
    return good[:max_points]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/analyze",
    response_model=ScoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Market Scout — Full Step 2 Pipeline (Firecrawl + LLM)",
)
async def _run_market_scout_logic(body: ScoutRequest) -> ScoutResponse:
    """
    Core reusable logic for market scouting pipeline.
    """
    logger.info(f"🔍 Market Scout: product='{body.product_name}', category='{body.category}'")

    fc = _get_firecrawl()
    credits_used = 0
    data_sources: List[str] = []
    competitor_texts: List[str] = []
    competitor_results: List[CompetitorResult] = []
    trending_content: List[ContentTrend] = []

    # ── 1. Firecrawl Search ────────────────────────────────────────────────────
    if fc:
        # Build search queries
        extra_kw = " ".join(body.keywords or [])
        queries = [
            f"{body.category} {body.product_name} competitor review {extra_kw}".strip(),
            f"best {body.category} products 2025 {body.region} comparison",
            f"{body.category} audience pain points complaints reddit",
        ]

        search_results_all = []
        for q in queries:
            results = await asyncio.to_thread(_firecrawl_search, fc, q, limit=4)
            search_results_all.extend(results)
            credits_used += 2  # 2 credits per 10 results

        # Deduplicate by URL
        seen_urls = set()
        for item in search_results_all:
            url = item.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            title = item.get("title", "")[:120]
            desc = item.get("description", "")[:300]
            md = item.get("markdown", "")
            key_pts = _extract_key_points(md or desc)

            competitor_results.append(CompetitorResult(
                url=url,
                title=title,
                description=desc,
                source="firecrawl_search",
                key_points=key_pts,
            ))
            competitor_texts.append(f"Title: {title}\nDescription: {desc}\nContent: {md[:800]}")

            # Also add to trending if it's about the category/trends
            if any(kw in url.lower() or kw in title.lower()
                   for kw in ["trend", "best", "review", "top", "2025"]):
                trending_content.append(ContentTrend(
                    title=title,
                    url=url,
                    source="web",
                    relevance_snippet=desc[:200],
                ))

        data_sources.append("firecrawl_search")

    # ── 2. Optional URL Scraping ───────────────────────────────────────────────
    if fc and body.competitor_urls:
        for url in (body.competitor_urls or [])[:3]:  # cap at 3 to limit credits
            scraped = await asyncio.to_thread(_firecrawl_scrape, fc, url)
            credits_used += 1  # 1 credit per page
            md = scraped.get("markdown", "")
            meta = scraped.get("metadata", {}) or {}
            title = meta.get("title") or url
            desc = meta.get("description") or ""
            key_pts = _extract_key_points(md)

            if md or desc:
                competitor_results.insert(0, CompetitorResult(
                    url=url,
                    title=title[:120],
                    description=desc[:300],
                    source="firecrawl_scrape",
                    key_points=key_pts,
                ))
                competitor_texts.insert(0, f"[COMPETITOR SITE] {title}\n{md[:1500]}")
                data_sources.append("firecrawl_scrape")

    # ── 3. LLM Gap Analysis ────────────────────────────────────────────────────
    if not competitor_texts:
        # No Firecrawl? Use fallback placeholder texts
        competitor_texts = [
            f"Category: {body.category}. Product: {body.product_name}. "
            "Limited web data available — using knowledge-based analysis."
        ]
        data_sources.append("llm_knowledge_fallback")
    else:
        data_sources.append("azure_openai_gpt4o")

    raw_gaps = await _run_gap_analysis(body.product_name, body.category, competitor_texts)

    gap_analysis = GapAnalysis(
        top_questions=raw_gaps.get("top_questions", [])[:5],
        complaints=raw_gaps.get("complaints", [])[:5],
        viral_hooks=raw_gaps.get("viral_hooks", [])[:5],
        opportunity_gap=raw_gaps.get("opportunity_gap", "Analysis complete."),
        recommended_angles=raw_gaps.get("recommended_angles", [])[:5],
    )

    return ScoutResponse(
        product_name=body.product_name,
        category=body.category,
        competitor_results=competitor_results[:10],
        trending_content=trending_content[:8],
        gap_analysis=gap_analysis,
        firecrawl_credits_used=credits_used,
        data_sources=list(dict.fromkeys(data_sources)),
    )

@router.post(
    "/analyze",
    response_model=ScoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Market Scout — Full Step 2 Pipeline (Firecrawl + LLM)",
)
async def market_scout_analyze(
    body: ScoutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Full market scouting pipeline:
    1. Firecrawl web search → competitor content + trending posts
    2. Optional direct URL scraping
    3. LLM gap analysis on all collected content
    """
    return await _run_market_scout_logic(body)


@router.post("/research-via-bot", summary="Trigger Market Scout via WhatsApp Bot")
async def research_via_bot(req: BotScoutRequest):
    import asyncio
    import httpx
    
    async def bg_scout():
        webhook_url = "http://localhost:8001/api/v1/whatsapp/system-alert"
        try:
            body = ScoutRequest(
                product_name=req.product_name,
                category=req.category,
                keywords=[],
                region="IN"
            )
            res: ScoutResponse = await _run_market_scout_logic(body)
            
            # Format the answer for WhatsApp
            msg = f"📊 *Market Scout Report: {req.product_name}*\n\n"
            msg += f"💡 *Opportunity Gap:*\n_{res.gap_analysis.opportunity_gap}_\n\n"
            msg += "*Top Questions from Customers:*\n"
            for q in res.gap_analysis.top_questions[:3]:
                msg += f"• {q}\n"
            msg += "\n*Winning Viral Hooks:*\n"
            for h in res.gap_analysis.viral_hooks[:3]:
                msg += f"• {h}\n"
            msg += "\n*Recommended Angles:*\n"
            for r in res.gap_analysis.recommended_angles[:2]:
                msg += f"• {r}\n"
                
            payload = {
                "user_id": req.user_id,
                "phone_number": req.phone_number,
                "phone_number_id": req.phone_number_id,
                "message": msg
            }
            
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                print("Sending market scout report to plugin webhook:", webhook_url)
                await http_client.post(webhook_url, json=payload)
                
        except Exception as e:
            logger.error(f"WhatsApp research failed: {e}")
            try:
                async with httpx.AsyncClient(timeout=10.0) as http_client:
                    await http_client.post(webhook_url, json={
                        "user_id": req.user_id,
                        "phone_number": req.phone_number,
                        "phone_number_id": req.phone_number_id,
                        "message": f"❌ Failed to run market research. Error: {e}"
                    })
            except Exception as e2:
                print(f"Failed to send error alert: {e2}")

    asyncio.create_task(bg_scout())
    return {"status": "queued"}


@router.get(
    "/trending",
    summary="Quick Firecrawl trend snapshot for a category",
)
async def get_trending(
    current_user: Annotated[User, Depends(get_current_user)],
    category: str = Query(..., description="Category to trend-search"),
    limit: int = Query(6, ge=1, le=10),
):
    """Fast 2-credit Firecrawl search for trending content in a category."""
    fc = _get_firecrawl()
    if not fc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firecrawl not configured. Set FIRECRAWL_API_KEY in .env.",
        )

    query = f"{category} trending viral content creators 2025"
    results = await asyncio.to_thread(_firecrawl_search, fc, query, limit=limit)

    return {
        "category": category,
        "credits_used": 2,
        "results": [
            {
                "title": r.get("title", "")[:120],
                "url": r.get("url", ""),
                "description": r.get("description", "")[:250],
            }
            for r in results
            if r.get("url")
        ],
    }
