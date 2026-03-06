import asyncio
import html
import json
import logging
import math
import re
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.agents.neural_render import (
    RenderBackend,
    RenderQuality,
    RenderRequest,
    get_render_agent,
)
from backend.app.agents.vision_dna import VisionDNAAgent, get_vision_dna_agent
from backend.app.core.config import settings
from backend.app.core.security import get_current_user
from backend.app.db.base import get_db
from backend.app.db.models import GeneratedCampaign, Job, ProductEmbedding, Project, User
from backend.app.db.schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssetDownloadLink,
    CampaignGenerationResponse,
    CampaignScoreBreakdown,
    CategoryTrendAnalysisResponse,
    CategoryTrendRequest,
    CompetitorAnalysisRequest,
    FullCampaignPipelineRequest,
    FullCampaignPipelineResponse,
    GapAnalysisResult,
    IdentityExtractionLiteRequest,
    IdentityExtractionLiteResponse,
    MarketIntelResponse,
    ProductCampaignBriefRequest,
    SystemPromptRequest,
    SystemPromptResponse,
)
from backend.app.services.analytics_service import AnalyticsService
from backend.app.services.market_intel_service import (
    MarketIntelService,
    MarketIntelService,
    get_market_intel_service,
)
from backend.app.services.rag_service import get_rag_service
from backend.app.services.transcript_feature_extractor import TranscriptFeatureExtractor
from backend.app.db.schemas import JobStatus
from backend.app.db.base import SessionLocal

router = APIRouter()
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEMO_OUTPUT_DIR = PROJECT_ROOT / "backend" / "output" / "demo_assets"
DEMO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/download", summary="Download generated asset")
async def download_file(path: str):
    """Serve a file from the project directory (e.g. generated assets)."""
    # Prevent absolute path traversal
    path = path.lstrip("/").lstrip("\\")

    # Defensive check
    if ".." in path:
        raise HTTPException(status_code=403, detail="Invalid path")
    
    full_path = (PROJECT_ROOT / path).resolve()
    
    # Ensure it's inside project root
    if not str(full_path).startswith(str(PROJECT_ROOT.resolve())):
         raise HTTPException(status_code=403, detail="Access denied")

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(full_path)


def _safe_slug(text: str, max_len: int = 42) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "campaign").strip().lower()).strip("-")
    return (cleaned or "campaign")[:max_len]


def _normalize_category_bucket(category: str) -> str:
    value = (category or "").lower()
    if any(k in value for k in ["tech", "laptop", "phone", "ai", "software", "gadget"]):
        return "Tech"
    if any(k in value for k in ["fashion", "clothing", "apparel", "style"]):
        return "Fashion"
    if any(k in value for k in ["finance", "fintech", "investment", "bank", "money"]):
        return "Finance"
    return "General"


def _relative_project_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except Exception:
        return path.name


def _download_url(path: Path) -> str:
    rel_path = _relative_project_path(path)
    return f"{settings.API_V1_STR}/market-intel/download?path={quote(rel_path)}"


def _is_allowed_download_path(file_path: Path) -> bool:
    candidate = file_path.resolve()
    allowed_roots = [
        (PROJECT_ROOT / "backend" / "output").resolve(),
        (PROJECT_ROOT / "backend" / "renders").resolve(),
        (PROJECT_ROOT / "output").resolve(),
        (PROJECT_ROOT / "renders").resolve(),
    ]
    return any(str(candidate).startswith(str(root)) for root in allowed_roots)


def _resolve_local_file(path_str: Optional[str]) -> Optional[Path]:
    if not path_str:
        return None

    p = Path(path_str)
    candidates = []
    if p.is_absolute():
        candidates.append(p)
    else:
        candidates.extend([
            (PROJECT_ROOT / path_str),
            (PROJECT_ROOT / "backend" / path_str),
            (PROJECT_ROOT / "backend" / "output" / Path(path_str).name),
            (PROJECT_ROOT / "backend" / "renders" / Path(path_str).name),
            (PROJECT_ROOT / "renders" / Path(path_str).name),
            Path.cwd() / path_str,
        ])

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            if resolved.exists() and resolved.is_file():
                return resolved
        except Exception:
            continue

    return None


def _build_poster_svg(product_name: str, idea: str, index: int) -> Path:
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = DEMO_OUTPUT_DIR / f"{_safe_slug(product_name)}_poster_{index}_{stamp}.svg"

    wrapped_lines = textwrap.wrap(idea, width=38)[:5] or ["Campaign concept"]
    tspan = "".join(
        f"<tspan x='70' dy='40'>{html.escape(line)}</tspan>" for line in wrapped_lines
    )

    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='1080' height='1350' viewBox='0 0 1080 1350'>
  <defs>
    <linearGradient id='bg' x1='0%' y1='0%' x2='100%' y2='100%'>
      <stop offset='0%' stop-color='#0e1a3d' />
      <stop offset='100%' stop-color='#1d5fff' />
    </linearGradient>
  </defs>
  <rect width='1080' height='1350' fill='url(#bg)'/>
  <text x='70' y='140' fill='#9be7ff' font-size='40' font-family='Arial, sans-serif'>Catalyst Nexus AI Poster</text>
  <text x='70' y='230' fill='#ffffff' font-size='62' font-weight='bold' font-family='Arial, sans-serif'>{html.escape(product_name)}</text>
  <text x='70' y='320' fill='#d6e4ff' font-size='42' font-family='Arial, sans-serif'>Concept #{index}</text>
  <text x='70' y='430' fill='#ffffff' font-size='34' font-family='Arial, sans-serif'>{tspan}</text>
  <rect x='70' y='1120' width='940' height='110' rx='20' fill='rgba(255,255,255,0.15)'/>
  <text x='100' y='1190' fill='#ffffff' font-size='34' font-family='Arial, sans-serif'>Download • Publish • Track • Learn</text>
</svg>"""

    out_path.write_text(svg, encoding="utf-8")
    return out_path


def _build_video_blueprint(product_name: str, motion_prompt: str) -> Path:
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = DEMO_OUTPUT_DIR / f"{_safe_slug(product_name)}_video_blueprint_{stamp}.md"
    content = f"""# Video Blueprint - {product_name}

Generated at: {datetime.utcnow().isoformat()}Z

## Motion Prompt
{motion_prompt}

## Production Notes
- Use brand-safe color palette from identity vault output.
- Prioritize first 2-second hook and clear CTA.
- Create vertical (9:16) and square (1:1) variants for social channels.
"""
    out_path.write_text(content, encoding="utf-8")
    return out_path


def _extract_gap_terms(content_gaps: List[str]) -> List[str]:
    terms: List[str] = []
    for gap in content_gaps or []:
        words = [w for w in re.findall(r"[a-zA-Z]{4,}", gap.lower()) if w not in {"that", "with", "from", "lack", "around"}]
        terms.extend(words[:3])
    return list(dict.fromkeys(terms))


def _estimate_gap_coverage(campaign: CampaignGenerationResponse, gap_terms: List[str]) -> float:
    if not gap_terms:
        return 0.55

    all_ideas = " ".join(
        (campaign.blog_ideas or [])
        + (campaign.tweet_ideas or [])
        + (campaign.reel_ideas or [])
        + (campaign.short_video_ideas or [])
        + (campaign.poster_ideas or [])
    ).lower()
    matched = sum(1 for t in gap_terms if t in all_ideas)
    return min(1.0, matched / max(1, len(gap_terms)))


def _make_competitor_matrix(top_posts: List[Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for post in (top_posts or [])[:8]:
        views = float(post.views or 0)
        engagement_rate = float(post.engagement_rate or 0)
        score = min(100.0, 32 + (engagement_rate * 950) + (math.log10(max(views, 1) + 1) * 9))
        rows.append({
            "source": "competitor",
            "title": post.title,
            "author": post.author or "unknown",
            "views": int(views),
            "engagement_rate": round(engagement_rate, 4),
            "score": round(score, 2),
        })
    return rows


def _normalize_competitor_handles(raw_handles: List[str], category: str) -> List[str]:
    handles = [h.strip() for h in (raw_handles or []) if h and h.strip()]
    if handles:
        return handles[:5]
    return [f"{category} trends", f"{category} india"]


async def _collect_competitor_analyses(
    handles: List[str],
    service: MarketIntelService,
    region_code: str,
    category: str,
    max_results: int,
) -> List[GapAnalysisResult]:
    """
    API-first competitor analysis for reliability.

    Avoids Instagram scraping in full-pipeline flow because that can hit
    429/rate-limit and stall demo runs for long periods.
    """
    analyses: List[GapAnalysisResult] = []
    for handle in handles[:3]:
        clean_handle = (handle or "").strip()
        if not clean_handle:
            continue

        trend_query = clean_handle if " " in clean_handle else f"{clean_handle} {category}"
        try:
            trend = await asyncio.wait_for(
                service.analyze_category_trends(
                    category=trend_query,
                    platform="youtube",
                    region_code=region_code,
                    max_results=max(4, min(max_results, 10)),
                ),
                timeout=20.0,
            )
            analyses.append(
                GapAnalysisResult(
                    competitor=clean_handle,
                    top_questions=[f"What hooks in {clean_handle} are currently outperforming?"],
                    complaints=(trend.content_gaps or [])[:3],
                    viral_hooks=(trend.recommended_hooks or [])[:3],
                    opportunity_gap=(
                        f"API-first trend scan ({trend.data_source}). "
                        f"Top keywords: {', '.join((trend.top_keywords or [])[:6]) or 'N/A'}"
                    ),
                )
            )
        except Exception as exc:
            analyses.append(
                GapAnalysisResult(
                    competitor=clean_handle,
                    top_questions=[],
                    complaints=[],
                    viral_hooks=[],
                    opportunity_gap=f"Fast analysis fallback: {exc}",
                )
            )
    return analyses


def _build_gap_analysis_payload(analyses: List[GapAnalysisResult], campaign: CampaignGenerationResponse) -> Dict[str, Any]:
    top_questions: List[str] = []
    complaints: List[str] = []
    hooks: List[str] = []
    for a in analyses:
        top_questions.extend(a.top_questions[:2])
        complaints.extend(a.complaints[:2])
        hooks.extend(a.viral_hooks[:2])

    trend_gaps = campaign.category_trend_analysis.content_gaps[:4]
    return {
        "top_unanswered_questions": list(dict.fromkeys(top_questions))[:6],
        "top_complaints": list(dict.fromkeys(complaints))[:6],
        "winning_hooks_from_market": list(dict.fromkeys(hooks))[:6],
        "market_gaps": trend_gaps,
        "recommended_positioning": campaign.campaign_strategy,
    }


async def _generate_poster_assets(
    request: FullCampaignPipelineRequest,
    campaign: CampaignGenerationResponse,
    visual_dna: Optional[Dict[str, Any]] = None,
    image_source: Optional[str] = None,
) -> List[AssetDownloadLink]:
    poster_assets: List[AssetDownloadLink] = []
    render_agent = get_render_agent()

    # Build DNA-aware style directives from extracted Visual DNA
    dna_style = ""
    if visual_dna:
        materials = visual_dna.get("materials", {})
        colors = materials.get("color_palette", [])
        surface = materials.get("surface_finish", "")
        primary_mat = materials.get("primary_material", "")
        structure = visual_dna.get("structure", {})
        features = structure.get("distinctive_features", [])

        dna_parts = []
        if colors:
            dna_parts.append(f"Color palette: {', '.join(colors[:5])}")
        if surface:
            dna_parts.append(f"Surface finish: {surface}")
        if primary_mat:
            dna_parts.append(f"Material: {primary_mat}")
        if features:
            dna_parts.append(f"Key features: {', '.join(features[:3])}")
        if dna_parts:
            dna_style = " Visual identity: " + "; ".join(dna_parts) + "."

    # Prepare reference images for identity-preserving generation
    ref_images = [image_source] if image_source else None

    for idx, idea in enumerate((campaign.poster_ideas or [])[: request.poster_generation_count], start=1):
        local_path: Optional[Path] = None
        # Build a rich, product-specific + DNA-aware prompt
        poster_prompt = (
            f"Professional marketing poster for '{request.product_name}' "
            f"({request.product_description[:120]}). "
            f"Category: {request.category}. Concept: {idea}. "
            f"High-end commercial photography style, clean modern design."
            f"{dna_style}"
        )
        try:
            preferred_backend = RenderBackend.DALLE_3
            render_result = await asyncio.wait_for(
                render_agent.render_image(
                    RenderRequest(
                        prompt=poster_prompt,
                        width=1024,
                        height=1024,
                        quality=RenderQuality.DRAFT,
                        backend=preferred_backend,
                        reference_images=ref_images,
                    )
                ),
                timeout=60.0,
            )
            local_path = _resolve_local_file(render_result.output_path)
            logger.info(f"[POSTER] Generated poster {idx} via DALL-E: {local_path}")
        except Exception as e:
            import traceback
            logger.error(f"[POSTER] DALL-E 3 poster {idx} failed (falling back to SVG): {e}")
            logger.error(traceback.format_exc())
            local_path = None

        if not local_path:
            local_path = _build_poster_svg(request.product_name, idea, idx)
            logger.warning(f"[POSTER] Using SVG fallback for poster {idx}: {local_path}")

        poster_assets.append(
            AssetDownloadLink(
                name=local_path.name,
                asset_type="poster",
                path=_relative_project_path(local_path),
                download_url=_download_url(local_path),
            )
        )

    return poster_assets


async def _generate_video_asset(
    request: FullCampaignPipelineRequest,
    campaign: CampaignGenerationResponse,
    image_source: Optional[str],
) -> Optional[AssetDownloadLink]:
    if not request.video_generation_enabled:
        return None

    # Reliability guard: if runtime video generation is disabled, return a
    # downloadable production blueprint immediately rather than waiting on
    # external providers.
    if not settings.VIDEO_GENERATION_ENABLED:
        motion_prompt = (
            (campaign.short_video_ideas or [None])[0]
            or (campaign.reel_ideas or [None])[0]
            or f"Cinematic product showcase for {request.product_name}"
        )
        local_path = _build_video_blueprint(request.product_name, motion_prompt)
        return AssetDownloadLink(
            name=local_path.name,
            asset_type="video_blueprint",
            path=_relative_project_path(local_path),
            download_url=_download_url(local_path),
        )

    render_agent = get_render_agent()
    motion_prompt = (
        (campaign.short_video_ideas or [None])[0]
        or (campaign.reel_ideas or [None])[0]
        or f"Cinematic product showcase for {request.product_name}"
    )

    # Prepare reference images for identity-preserving video generation
    ref_images = [image_source] if image_source else None

    # Build a product-anchored video prompt
    video_prompt = (
        f"Cinematic product video for '{request.product_name}' "
        f"({request.product_description[:150]}). "
        f"Category: {request.category}. "
        f"Script concept: {motion_prompt}. "
        f"Professional commercial style, product-focused visuals."
    )
    logger.info(f"[VIDEO] Generating video for '{request.product_name}': {video_prompt[:200]}")

    local_path: Optional[Path] = None
    try:
        if not local_path:
            # Use OpenAI Sora-2 API as requested by user
            preferred_video_backend = RenderBackend.SORA_2
            render_result = await asyncio.wait_for(
                render_agent.render_video(
                    RenderRequest(
                        prompt=video_prompt,
                        width=1280,
                        height=720,
                        duration_seconds=max(5, min(20, request.video_duration_seconds)),
                        quality=RenderQuality.STANDARD,
                        backend=preferred_video_backend,
                        reference_images=ref_images,
                    )
                ),
                timeout=180.0,
            )
            local_path = _resolve_local_file(render_result.output_path)
            logger.info(f"[VIDEO] Generated video via Sora-2: {local_path}")
    except Exception as e:
        logger.error(f"[VIDEO] Video generation failed: {type(e).__name__}: {e}")
        local_path = None

    if not local_path:
        local_path = _build_video_blueprint(request.product_name, motion_prompt)
        logger.warning(f"[VIDEO] Using blueprint fallback: {local_path}")
        return AssetDownloadLink(
            name=local_path.name,
            asset_type="video_blueprint",
            path=_relative_project_path(local_path),
            download_url=_download_url(local_path),
        )

    return AssetDownloadLink(
        name=local_path.name,
        asset_type="video",
        path=_relative_project_path(local_path),
        download_url=_download_url(local_path),
    )


def _compute_scoring(
    request: FullCampaignPipelineRequest,
    campaign: CampaignGenerationResponse,
    competitor_matrix: List[Dict[str, Any]],
) -> CampaignScoreBreakdown:
    category_bucket = _normalize_category_bucket(request.category)
    feature_vector = TranscriptFeatureExtractor.generate_synthetic(category_bucket)
    feature_map = TranscriptFeatureExtractor.vector_to_dict(feature_vector)

    competitor_scores = [float(r.get("score", 0)) for r in competitor_matrix if r.get("source") == "competitor"]
    competitor_baseline = sum(competitor_scores) / len(competitor_scores) if competitor_scores else 54.0

    gap_terms = _extract_gap_terms(campaign.category_trend_analysis.content_gaps)
    gap_coverage = _estimate_gap_coverage(campaign, gap_terms)

    hook_strength = float(feature_map.get("hook_strength", 0.5))
    cta_density = float(feature_map.get("cta_density", 0.25))
    urgency = float(feature_map.get("urgency_score", 0.2))
    idea_volume_bonus = min(
        8.0,
        (len(campaign.reel_ideas) + len(campaign.short_video_ideas) + len(campaign.poster_ideas)) / 2.0,
    )

    ai_score = min(
        99.0,
        competitor_baseline
        + 6.5
        + hook_strength * 11.0
        + cta_density * 6.0
        + urgency * 4.0
        + gap_coverage * 14.0
        + idea_volume_bonus,
    )
    competitor_score = min(95.0, max(35.0, competitor_baseline))
    uplift = ((ai_score - competitor_score) / max(1.0, competitor_score)) * 100.0

    verdict = (
        "Ranked above competitor benchmark"
        if ai_score >= competitor_score + 4
        else "Competitive, but needs stronger creative hooks"
    )

    factors = [
        f"Gap coverage: {gap_coverage * 100:.1f}%",
        f"Hook strength signal: {hook_strength:.2f}",
        f"CTA density signal: {cta_density:.2f}",
        f"Urgency signal: {urgency:.2f}",
        f"Idea volume bonus: {idea_volume_bonus:.1f}",
    ]

    return CampaignScoreBreakdown(
        ai_score=round(ai_score, 2),
        competitor_score=round(competitor_score, 2),
        uplift_percent=round(uplift, 2),
        verdict=verdict,
        factors=factors,
        feature_vector={k: round(float(v), 4) for k, v in feature_map.items()},
    )

@router.post("/analyze", response_model=MarketIntelResponse)
async def analyze_competitors(
    request: CompetitorAnalysisRequest,
    current_user: User = Depends(get_current_user),
    service: MarketIntelService = Depends(get_market_intel_service)
):
    """
    Scrape and analyze competitor profiles to find market gaps.
    """
    analyses = []
    
    # 1. Analyze each competitor (sequentially to be safe with rate limits/credits)
    try:
        for username in request.usernames:
            clean_username = (username or "").strip()
            if not clean_username:
                continue
            # If input looks like a search phrase/category (e.g. "nike shoes"),
            # use API-first trend analysis (YouTube/Brave) instead of Instagram profile scraping.
            if " " in clean_username:
                trend = await service.analyze_category_trends(
                    category=clean_username,
                    platform="youtube",
                    region_code="IN",
                    max_results=8,
                )
                analyses.append(GapAnalysisResult(
                    competitor=clean_username,
                    top_questions=[f"What content angle wins in {clean_username} right now?"],
                    complaints=trend.content_gaps[:3] if getattr(trend, "content_gaps", None) else [],
                    viral_hooks=trend.recommended_hooks[:3] if getattr(trend, "recommended_hooks", None) else [],
                    opportunity_gap=(
                        f"Data source: {getattr(trend, 'data_source', 'unknown')}. "
                        f"Top keywords: {', '.join((getattr(trend, 'top_keywords', []) or [])[:6]) or 'N/A'}"
                    )
                ))
                continue
            try:
                result = await service.analyze_competitor(clean_username)
                analyses.append(result)
            except Exception as e:
                # Don't fail the whole request if one fails
                analyses.append(GapAnalysisResult(
                    competitor=clean_username,
                    top_questions=[],
                    complaints=[],
                    viral_hooks=[],
                    opportunity_gap=f"Error analyzing: {str(e)}"
                ))
    except Exception as e:
        analyses.append(GapAnalysisResult(
            competitor="system",
            top_questions=[],
            complaints=[],
            viral_hooks=[],
            opportunity_gap=f"Analysis pipeline failed safely: {str(e)}"
        ))
    
    # 2. Consolidate results (optional: use LLM again to synthesize all)
    # For now, just concatenate opportunity gaps
    consolidated_strategy = "Based on the analysis, here is the opportunity: "
    for analysis in analyses:
         if analysis.opportunity_gap and "Error" not in analysis.opportunity_gap:
             consolidated_strategy += f"\n- {analysis.competitor}: {analysis.opportunity_gap}"
             
    return MarketIntelResponse(
        analyses=analyses,
        consolidated_strategy=consolidated_strategy
    )


# ═════════════════════════════════════════════════════════════════════════════
# MEDIA RENDER — Now handled by ARQ worker (see backend/app/worker.py)
# The API only enqueues the job to Redis. The worker picks it up.
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/full-pipeline", response_model=FullCampaignPipelineResponse)
async def run_full_campaign_pipeline(
    request: FullCampaignPipelineRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: MarketIntelService = Depends(get_market_intel_service),
    vision_agent: VisionDNAAgent = Depends(get_vision_dna_agent),
):
    """Run end-to-end campaign pipeline: identity vault -> market intel -> scoring -> assets."""
    if current_user.wallet_balance < 100:
        raise HTTPException(status_code=402, detail="Insufficient credits. Required: $1.00")

    project = Project(
        name=f"{request.product_name} Demo Campaign",
        product_name=request.product_name,
        description=request.product_description,
        owner_id=current_user.id,
        settings={"source": "full-pipeline", "category": request.category},
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    image_source = request.product_image_data_url or request.product_image_url
    if image_source and not image_source.startswith(("http://", "https://", "data:image")):
        maybe_local = _resolve_local_file(image_source)
        if maybe_local:
            image_source = str(maybe_local)

    identity_payload: Dict[str, Any] = {
        "project_id": str(project.id),
        "status": "skipped",
        "reason": "No product image provided",
    }

    # ── Use pre-computed Visual DNA from progressive pipeline if available ──
    if request.visual_dna_precomputed:
        logger.info("[PIPELINE] Using pre-computed Visual DNA from progressive pipeline (skipping extraction)")
        identity_payload = {
            "project_id": str(project.id),
            "status": "stored",
            "confidence": request.visual_dna_precomputed.get("confidence_score", 0.8),
            "visual_dna": request.visual_dna_precomputed,
        }
        # Still try to store embedding if we have an image, but don't block on it
        if image_source:
            try:
                extraction = await vision_agent.extract_product_identity(
                    image_sources=[image_source],
                    product_name=request.product_name,
                    additional_context=request.identity_notes,
                )
                embedding_row = ProductEmbedding(
                    project_id=project.id,
                    version_label="v1.0",
                    visual_dna_json={
                        **request.visual_dna_precomputed,
                        "product_name": request.product_name,
                        "source_images": [image_source],
                        "identity_notes": request.identity_notes,
                    },
                    embedding_vector=extraction.embedding,
                    is_active=True,
                )
                db.add(embedding_row)
                db.commit()
                db.refresh(embedding_row)
                identity_payload["embedding_id"] = str(embedding_row.id)
            except Exception as exc:
                logger.warning(f"[PIPELINE] Embedding storage failed (non-blocking): {exc}")
    elif image_source:
        try:
            extraction = await vision_agent.extract_product_identity(
                image_sources=[image_source],
                product_name=request.product_name,
                additional_context=request.identity_notes,
            )

            embedding_row = ProductEmbedding(
                project_id=project.id,
                version_label="v1.0",
                visual_dna_json={
                    **extraction.visual_dna.to_dict(),
                    "product_name": request.product_name,
                    "source_images": [image_source],
                    "identity_notes": request.identity_notes,
                },
                embedding_vector=extraction.embedding,
                is_active=True,
            )
            db.add(embedding_row)
            db.commit()
            db.refresh(embedding_row)

            identity_payload = {
                "project_id": str(project.id),
                "embedding_id": str(embedding_row.id),
                "status": "stored",
                "confidence": extraction.confidence,
                "visual_dna": extraction.visual_dna.to_dict(),
            }
        except Exception as exc:
            identity_payload = {
                "project_id": str(project.id),
                "status": "failed",
                "reason": str(exc),
            }

    competitor_handles = _normalize_competitor_handles(request.competitor_handles, request.category)
    competitor_analyses = await _collect_competitor_analyses(
        handles=competitor_handles,
        service=service,
        region_code=request.region_code,
        category=request.category,
        max_results=request.max_trend_results,
    )

    # ── Extract visual DNA context for campaign generation ──────────────────
    visual_dna_dict = identity_payload.get("visual_dna") if identity_payload.get("status") == "stored" else None

    # ── Distill competitor insights for the LLM ──────────────────────────────
    competitor_insight_list = None
    if competitor_analyses:
        competitor_insight_list = [
            {
                "competitor": a.competitor,
                "opportunity_gap": a.opportunity_gap,
                "viral_hooks": a.viral_hooks[:3] if a.viral_hooks else [],
                "top_questions": a.top_questions[:3] if a.top_questions else [],
            }
            for a in competitor_analyses
        ]

    campaign_request = ProductCampaignBriefRequest(
        product_name=request.product_name,
        product_description=request.product_description,
        category=request.category,
        target_audience=request.target_audience,
        product_image_url=request.product_image_url,
        product_image_name=request.product_image_name,
        identity_notes=request.identity_notes,
        region_code=request.region_code,
        video_generation_enabled=request.video_generation_enabled,
        system_prompt=request.system_prompt,
        visual_dna=visual_dna_dict,
        competitor_insights=competitor_insight_list,
    )
    campaign = await service.generate_campaign_from_product(campaign_request)

    competitor_matrix = _make_competitor_matrix(campaign.category_trend_analysis.top_posts)
    scoring = _compute_scoring(request=request, campaign=campaign, competitor_matrix=competitor_matrix)

    competitor_matrix.append(
        {
            "source": "our_campaign",
            "title": request.product_name,
            "author": "Catalyst Nexus AI",
            "views": None,
            "engagement_rate": None,
            "score": scoring.ai_score,
            "benchmark": scoring.competitor_score,
            "uplift_percent": scoring.uplift_percent,
        }
    )

    gap_analysis = _build_gap_analysis_payload(competitor_analyses, campaign)

    # ── Create a background Job for media rendering ────────────────────────
    media_job = Job(
        job_type="media_render",
        status=JobStatus.PENDING.value,
        parameters={
            "product_name": request.product_name,
            "poster_count": request.poster_generation_count,
            "video_enabled": request.video_generation_enabled,
        },
        project_id=project.id,
        user_id=current_user.id,
        priority=3,
        status_message="Queued for media rendering...",
        progress=0,
    )
    db.add(media_job)
    db.commit()
    db.refresh(media_job)
    media_job_id = str(media_job.id)

    downloads: Dict[str, str] = {}

    market_intel_payload = {
        "trend_analysis": campaign.category_trend_analysis.model_dump(mode="json"),
        "competitor_handles": competitor_handles,
        "competitor_analysis": [a.model_dump(mode="json") for a in competitor_analyses],
    }

    bundle_payload = {
        "identity_vault": identity_payload,
        "market_intel": market_intel_payload,
        "gap_analysis": gap_analysis,
        "competitor_matrix": competitor_matrix,
        "scoring": scoring.model_dump(mode="json"),
        "campaign": campaign.model_dump(mode="json"),
        "poster_assets": [],  # Will be filled by background job
        "video_asset": None,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    bundle_path = DEMO_OUTPUT_DIR / f"{_safe_slug(request.product_name)}_campaign_bundle_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    bundle_path.write_text(json.dumps(bundle_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    downloads["campaign_bundle"] = _download_url(bundle_path)

    # ── Persist to Supabase and Deduct Credits Atomically ───────────────────
    try:
        trend = campaign.category_trend_analysis
        gc = GeneratedCampaign(
            user_id=current_user.id,
            project_id=project.id,
            product_name=request.product_name,
            product_description=request.product_description,
            category=request.category,
            target_audience=request.target_audience,
            region_code=request.region_code,
            campaign_strategy=campaign.campaign_strategy,
            blog_ideas=campaign.blog_ideas or [],
            tweet_ideas=campaign.tweet_ideas or [],
            reel_ideas=campaign.reel_ideas or [],
            short_video_ideas=campaign.short_video_ideas or [],
            poster_ideas=campaign.poster_ideas or [],
            poster_assets=[],
            scoring=scoring.model_dump(mode="json"),
            competitor_matrix=competitor_matrix,
            gap_analysis=gap_analysis,
            trend_keywords=trend.top_keywords or [],
            content_gaps=trend.content_gaps or [],
        )
        db.add(gc)
        
        # Deduct credits atomically with campaign creation
        current_user.wallet_balance -= 100
        
        db.commit()
        db.refresh(gc)
        downloads["campaign_db_id"] = str(gc.id)

        # ── RAG Auto-Ingestion (inline, not via worker) ───────────────────────
        try:
            from backend.app.services.rag_service import get_rag_service
            rag = get_rag_service(db)
            ingested = await rag.ingest_campaign(gc)
            logger.info(f"✅ RAG ingestion complete: {ingested} chunks from campaign {gc.id}")
        except Exception as rag_exc:
            logger.warning(f"⚠️ RAG ingestion failed (non-blocking): {rag_exc}")

    except Exception as db_exc:
        db.rollback()
        logger.error(f"Failed to persist campaign or deduct credits, rolling back transaction: {db_exc}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to initiate campaign pipeline. Your credits have not been deducted. Please try again."
        )

    # ── Enqueue media rendering to Redis/ARQ worker ─────────────────────────
    try:
        from backend.app.core.redis import enqueue_media_render
        await enqueue_media_render(
            job_id=media_job_id,
            request_dict=request.model_dump(mode="json"),
            campaign_dict=campaign.model_dump(mode="json"),
            visual_dna_dict=visual_dna_dict,
            image_source=image_source,
            campaign_db_id=downloads.get("campaign_db_id"),
        )
    except Exception as enqueue_err:
        logger.error(f"Failed to enqueue media render to Redis: {enqueue_err}")
        # Job row already exists in DB with PENDING status;
        # the worker will pick it up on next poll or it can be retried.

    return FullCampaignPipelineResponse(
        identity_vault=identity_payload,
        market_intel=market_intel_payload,
        gap_analysis=gap_analysis,
        competitor_matrix=competitor_matrix,
        scoring=scoring,
        campaign=campaign,
        poster_assets=[],
        video_asset=None,
        downloads=downloads,
        media_render_job_id=media_job_id,
    )


@router.post("/analyze-category-trends", response_model=CategoryTrendAnalysisResponse)
async def analyze_category_trends(
    request: CategoryTrendRequest,
    current_user: User = Depends(get_current_user),
    service: MarketIntelService = Depends(get_market_intel_service),
):
    """Analyze trending content for a category and return actionable insights."""
    _ = current_user
    return await service.analyze_category_trends(
        category=request.category,
        platform=request.platform,
        region_code=request.region_code,
        max_results=request.max_results,
    )


@router.post("/generate-campaign-brief", response_model=CampaignGenerationResponse)
async def generate_campaign_brief(
    request: ProductCampaignBriefRequest,
    current_user: User = Depends(get_current_user),
    service: MarketIntelService = Depends(get_market_intel_service),
):
    """Generate blog/tweet/reel/short/poster strategy from product + trend data."""
    _ = current_user
    return await service.generate_campaign_from_product(request)


@router.post("/generate-system-prompt", response_model=SystemPromptResponse)
async def generate_system_prompt(
    request: SystemPromptRequest,
    current_user: User = Depends(get_current_user),
    service: MarketIntelService = Depends(get_market_intel_service),
):
    """Generate a dynamic system prompt for campaign generation based on category."""
    _ = current_user
    prompt_text = await service.generate_system_prompt(request.category, request.product_name)
    return SystemPromptResponse(system_prompt=prompt_text)


@router.post("/extract-identity-lite", response_model=IdentityExtractionLiteResponse)
async def extract_identity_lite(
    request: IdentityExtractionLiteRequest,
    current_user: User = Depends(get_current_user),
    vision_agent: VisionDNAAgent = Depends(get_vision_dna_agent),
):
    """Extract Visual DNA from a product image without creating a project.

    Used by the progressive pipeline to start identity extraction early
    (Step 0) so the data is ready by the time the user launches the campaign.
    """
    _ = current_user
    image_source = request.image_data_url or request.image_url
    if not image_source:
        return IdentityExtractionLiteResponse(
            status="skipped",
            error="No image provided",
        )

    try:
        extraction = await vision_agent.extract_product_identity(
            image_sources=[image_source],
            product_name=request.product_name,
            additional_context=request.identity_notes,
        )
        return IdentityExtractionLiteResponse(
            status="success",
            visual_dna=extraction.visual_dna.to_dict(),
            confidence=extraction.confidence,
        )
    except Exception as exc:
        logger.error(f"[IDENTITY-LITE] Extraction failed: {exc}")
        return IdentityExtractionLiteResponse(
            status="failed",
            error=str(exc),
        )


@router.post("/assistant-chat", response_model=AssistantChatResponse)
async def assistant_chat(
    request: AssistantChatRequest,
    current_user: User = Depends(get_current_user),
    service: MarketIntelService = Depends(get_market_intel_service),
    db: Session = Depends(get_db),
):
    _ = current_user
    analytics = AnalyticsService(db)
    live_context = {
        "dashboard": analytics.get_analytics_dashboard(days=30),
        "competitor_content_intel": analytics.get_competitor_content_intel(limit=5),
    }
    merged_context = {**(request.context or {}), **live_context}
    return await service.assistant_chat(
        message=request.message,
        history=request.history,
        context=merged_context,
        video_generation_enabled=request.video_generation_enabled,
        user_id=current_user.id,
        db=db,
    )


@router.get("/download")
async def download_generated_asset(
    path: str = Query(..., min_length=3),
    current_user: User = Depends(get_current_user),
):
    """Serve generated assets for authenticated users (posters, videos, bundles)."""
    _ = current_user
    normalized = path.replace("\\", "/").lstrip("/")
    candidate = (PROJECT_ROOT / normalized).resolve()

    if not _is_allowed_download_path(candidate):
        raise HTTPException(status_code=403, detail="Path is outside allowed download roots")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Requested asset not found")

    return FileResponse(candidate, filename=candidate.name, media_type="application/octet-stream")


from backend.app.db.schemas import BlogGenerationRequest, BlogGenerationResponse

@router.post("/generate-blog", response_model=BlogGenerationResponse)
async def generate_blog(
    request: BlogGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from backend.app.api.v1.assistant_chat import _gpt_chat
    
    if current_user.wallet_balance < 10:
        raise HTTPException(status_code=402, detail="Insufficient credits. Required: $0.10")
    
    system_prompt = "You are an expert marketing copywriter and SEO blog author."
    user_prompt = f"""Product: {request.product_name}
Campaign Strategy: {request.campaign_strategy}
Blog Idea: {request.idea}

Please write a high-quality, comprehensive, and engaging full-length blog post based on this idea. 
Use markdown formatting. Include an engaging introduction, structured body paragraphs with H2/H3 headings, and a strong call-to-action conclusion."""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    blog_content = await _gpt_chat(messages, temperature=0.7, max_tokens=1500)
    
    # Deduct credits
    current_user.wallet_balance -= 10
    db.commit()
    
    return BlogGenerationResponse(blog_content=blog_content)


from backend.app.db.schemas import ReelGenerationRequest, ReelGenerationResponse

@router.post("/generate-reel", response_model=ReelGenerationResponse)
async def generate_reel(
    request: ReelGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from backend.app.agents.neural_render import get_render_agent, RenderRequest, RenderQuality, RenderBackend
    from pathlib import Path
    
    if current_user.wallet_balance < 50:
        raise HTTPException(status_code=402, detail="Insufficient credits. Required: $0.50")
        
    render_agent = get_render_agent()
    
    prompt = f"{request.product_name} reel video based on concept: {request.idea}"
    
    # 1. Generate via Sora-2
    render_result = await asyncio.wait_for(
        render_agent.render_video(
            RenderRequest(
                prompt=prompt,
                duration_seconds=5.0,
                quality=RenderQuality.STANDARD,
                backend=RenderBackend.SORA_2
            )
        ),
        timeout=600.0  # Sora-2 often takes 2+ minutes to render
    )
    
    if render_result.status != "completed" or not render_result.output_path:
        raise HTTPException(status_code=500, detail="Failed to generate the reel video")
        
    local_path = Path(render_result.output_path).resolve()
    download_url = _download_url(local_path)
    
    # 2. Update existing campaign in DB if requested
    if request.campaign_id:
        try:
            from backend.app.db.models import GeneratedCampaign
            gc = db.query(GeneratedCampaign).filter(GeneratedCampaign.id == request.campaign_id).first()
            if gc:
                assets = list(gc.poster_assets or [])
                assets.append({
                    "name": local_path.name,
                    "download_url": download_url,
                    "asset_type": "video"
                })
                gc.poster_assets = assets
                db.commit()
                logger.info(f"Appended generated reel to campaign {gc.id}")
        except Exception as e:
            logger.warning(f"Could not persist generated reel to campaign: {e}")
            
    # Deduct credits
    current_user.wallet_balance -= 50
    db.commit()
            
    return ReelGenerationResponse(video_url=download_url, asset_name=local_path.name)
