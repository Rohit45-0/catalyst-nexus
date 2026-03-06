"""
Catalyst Nexus Orchestrator - LangGraph State Machine
======================================================

The "brain" of the video generation pipeline. Uses LangGraph to route tasks
through a stateful workflow:

    Research → Content → Motion → Render

Features:
- Checkpoint/resume for long-running jobs
- Human-in-the-loop approval gates
- Dynamic routing based on job type
- Progress tracking and status updates
- Error recovery and retry logic

Author: Catalyst Nexus Team
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Literal, TypedDict, Annotated, Callable
from enum import Enum
from datetime import datetime, UTC
from uuid import uuid4
import asyncio
import json
import logging
import operator

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
import httpx

from backend.app.core.config import settings
from backend.app.agents.vision_dna import VisionDNAAgent, ExtractionResult, get_vision_dna_agent
from backend.app.agents.publish_node import PublishNode

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    """Return timezone-aware UTC timestamp in ISO format."""
    return datetime.now(UTC).isoformat()


# =============================================================================
# STATE DEFINITIONS
# =============================================================================

class JobStatus(str, Enum):
    """Status of a generation job."""
    PENDING = "pending"
    RESEARCHING = "researching"
    GENERATING_CONTENT = "generating_content"
    CREATING_MOTION = "creating_motion"
    RENDERING = "rendering"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowType(str, Enum):
    """Types of generation workflows."""
    PRODUCT_VIDEO = "product_video"           # Full video from product images
    IDENTITY_EXTRACTION = "identity_extraction"  # Just extract product DNA
    CONTENT_ONLY = "content_only"             # Generate script/storyboard only
    MOTION_ONLY = "motion_only"               # Generate motion scaffold only
    RENDER_ONLY = "render_only"               # Render from existing scaffold
    FULL_PIPELINE = "full_pipeline"           # Complete end-to-end


class NexusState(TypedDict):
    """
    The state object passed through the LangGraph workflow.
    
    This is the central data structure that accumulates results
    from each stage of the pipeline.
    """
    # === Job Metadata ===
    job_id: str
    workflow_type: str
    status: str
    created_at: str
    updated_at: str
    
    # === Input Parameters ===
    project_id: str
    product_name: str
    product_images: List[str]
    brand_guidelines: Optional[Dict[str, Any]]
    target_audience: Optional[str]
    video_style: Optional[str]
    duration_seconds: float
    aspect_ratio: str
    
    # === Research Stage Output ===
    market_research: Optional[Dict[str, Any]]
    competitor_analysis: Optional[Dict[str, Any]]
    trending_hooks: Optional[List[str]]
    
    # === Content Stage Output ===
    product_identity: Optional[Dict[str, Any]]  # From VisionDNA
    script: Optional[str]
    storyboard: Optional[List[Dict[str, Any]]]
    voiceover_text: Optional[str]
    
    # === Motion Stage Output ===
    motion_scaffold: Optional[Dict[str, Any]]
    camera_movements: Optional[List[Dict[str, Any]]]
    keyframes: Optional[List[Dict[str, Any]]]
    
    # === Render Stage Output ===
    render_settings: Optional[Dict[str, Any]]
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    preview_frames: Optional[List[str]]

    # === Publish Stage Output ===
    publish_results: Optional[Dict[str, Any]]
    campaign_id: Optional[str]
    tracking_link: Optional[str]
    
    # === Progress Tracking ===
    current_stage: str
    progress_percent: float
    stage_messages: Annotated[List[str], operator.add]  # Append-only
    
    # === Error Handling ===
    errors: Annotated[List[str], operator.add]  # Append-only
    retry_count: int
    max_retries: int
    
    # === Control Flow ===
    needs_approval: bool
    approved: bool
    should_continue: bool
    auto_publish: bool
    publish_to_platforms: Optional[List[str]]
    publish_caption: Optional[str]


def create_initial_state(
    job_id: str,
    workflow_type: str,
    project_id: str,
    product_name: str,
    product_images: List[str],
    duration_seconds: float = 15.0,
    aspect_ratio: str = "16:9",
    **kwargs
) -> NexusState:
    """Create initial state for a new workflow execution."""
    now = utc_now_iso()
    
    return NexusState(
        # Metadata
        job_id=job_id,
        workflow_type=workflow_type,
        status=JobStatus.PENDING.value,
        created_at=now,
        updated_at=now,
        
        # Inputs
        project_id=project_id,
        product_name=product_name,
        product_images=product_images,
        brand_guidelines=kwargs.get("brand_guidelines"),
        target_audience=kwargs.get("target_audience"),
        video_style=kwargs.get("video_style", "professional"),
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        
        # Research outputs
        market_research=None,
        competitor_analysis=None,
        trending_hooks=None,
        
        # Content outputs
        product_identity=None,
        script=None,
        storyboard=None,
        voiceover_text=None,
        
        # Motion outputs
        motion_scaffold=None,
        camera_movements=None,
        keyframes=None,
        
        # Render outputs
        render_settings=None,
        video_url=None,
        thumbnail_url=None,
        preview_frames=None,

        # Publish outputs
        publish_results=None,
        campaign_id=None,
        tracking_link=None,
        
        # Progress
        current_stage="initialization",
        progress_percent=0.0,
        stage_messages=[f"[{now}] Job created: {job_id}"],
        
        # Errors
        errors=[],
        retry_count=0,
        max_retries=3,
        
        # Control
        needs_approval=False,
        approved=True,
        should_continue=True,
        auto_publish=kwargs.get("auto_publish", False),
        publish_to_platforms=kwargs.get("publish_to_platforms", ["instagram"]),
        publish_caption=kwargs.get("publish_caption"),
    )


# =============================================================================
# NODE IMPLEMENTATIONS
# =============================================================================

class ResearchNode:
    """
    Research Stage: Market analysis and trend discovery.
    
    Uses Brave Search API to gather:
    - Competitor video ads
    - Trending hooks/formats
    - Target audience insights
    """
    
    def __init__(self):
        self.brave_api_key = getattr(settings, 'BRAVE_API_KEY', None)
        self.azure_endpoint = settings.AZURE_OPENAI_ENDPOINT
        self.azure_api_key = settings.AZURE_OPENAI_API_KEY
    
    async def __call__(self, state: NexusState) -> NexusState:
        """Execute research stage."""
        logger.info(f"🔍 Research Stage - Job: {state['job_id']}")
        
        state["status"] = JobStatus.RESEARCHING.value
        state["current_stage"] = "research"
        state["progress_percent"] = 10.0
        state["updated_at"] = utc_now_iso()
        state["stage_messages"] = [f"[{state['updated_at']}] Starting market research..."]
        
        try:
            # Search for competitor ads and trends
            if self.brave_api_key:
                research_data = await self._search_market(
                    product_name=state["product_name"],
                    target_audience=state.get("target_audience", "general")
                )
                state["market_research"] = research_data.get("market_data")
                state["competitor_analysis"] = research_data.get("competitors")
                state["trending_hooks"] = research_data.get("hooks", [])
            else:
                # Fallback: Generate synthetic research
                state["trending_hooks"] = [
                    "Problem → Solution reveal",
                    "Before/After transformation",
                    "Unboxing experience",
                    "360° product showcase",
                    "Lifestyle integration"
                ]
                state["market_research"] = {
                    "generated": True,
                    "note": "Using default research (Brave API not configured)"
                }
            
            state["stage_messages"] = [
                f"[{utc_now_iso()}] ✅ Research complete - Found {len(state.get('trending_hooks', []))} hooks"
            ]
            state["progress_percent"] = 20.0
            
        except Exception as e:
            logger.error(f"Research failed: {e}")
            state["errors"] = [f"Research stage failed: {str(e)}"]
            # Continue anyway with defaults
            state["trending_hooks"] = ["Product showcase", "Feature highlight"]
        
        return state
    
    async def _search_market(self, product_name: str, target_audience: str) -> Dict[str, Any]:
        """Search for market data using Brave API."""
        query = f"{product_name} video ad marketing {target_audience}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": self.brave_api_key},
                params={"q": query, "count": 10}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "market_data": data.get("web", {}).get("results", [])[:5],
                    "competitors": [],
                    "hooks": self._extract_hooks(data)
                }
        
        return {"market_data": {}, "competitors": [], "hooks": []}
    
    def _extract_hooks(self, search_data: Dict) -> List[str]:
        """Extract potential video hooks from search results."""
        # Default hooks based on common video marketing patterns
        return [
            "Attention-grabbing opener",
            "Problem statement hook",
            "Product reveal moment",
            "Feature demonstration",
            "Call to action"
        ]


class ContentNode:
    """
    Content Stage: Identity extraction and script generation.
    
    Uses:
    - VisionDNA Agent for product identity
    - GPT-4o for script/storyboard generation
    """
    
    def __init__(self):
        self.vision_agent = get_vision_dna_agent()
        self.azure_endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        self.azure_api_key = settings.AZURE_OPENAI_API_KEY
        self.deployment_name = settings.AZURE_DEPLOYMENT_NAME
    
    async def __call__(self, state: NexusState) -> NexusState:
        """Execute content generation stage."""
        logger.info(f"📝 Content Stage - Job: {state['job_id']}")
        
        state["status"] = JobStatus.GENERATING_CONTENT.value
        state["current_stage"] = "content"
        state["progress_percent"] = 25.0
        state["updated_at"] = utc_now_iso()
        state["stage_messages"] = [f"[{state['updated_at']}] Extracting product identity..."]
        
        try:
            # Step 1: Extract product identity using VisionDNA
            if state["product_images"]:
                extraction = await self.vision_agent.extract_product_identity(
                    image_sources=state["product_images"],
                    product_name=state["product_name"],
                    additional_context=state.get("target_audience")
                )
                
                state["product_identity"] = {
                    "visual_dna": extraction.visual_dna.to_dict(),
                    "embedding": extraction.embedding[:10] + ["..."],  # Truncate for state
                    "confidence": extraction.confidence,
                    "motion_recommendations": extraction.visual_dna.motion_recommendations,
                    "camera_suggestions": extraction.visual_dna.camera_angle_suggestions,
                }
                
                state["progress_percent"] = 40.0
                state["stage_messages"] = [
                    f"[{utc_now_iso()}] ✅ Product identity extracted (confidence: {extraction.confidence:.0%})"
                ]
            
            # Step 2: Generate script and storyboard
            script_data = await self._generate_script(state)
            state["script"] = script_data.get("script")
            state["storyboard"] = script_data.get("storyboard")
            state["voiceover_text"] = script_data.get("voiceover")
            
            state["progress_percent"] = 50.0
            state["stage_messages"] = [
                f"[{utc_now_iso()}] ✅ Script and storyboard generated"
            ]
            
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            state["errors"] = [f"Content stage failed: {str(e)}"]
            state["should_continue"] = False
        
        return state
    
    async def _generate_script(self, state: NexusState) -> Dict[str, Any]:
        """Generate video script using GPT-4o."""
        
        # Build context from state
        product_info = (state.get("product_identity") or {}).get("visual_dna", {})
        hooks = state.get("trending_hooks", ["Product showcase"])
        duration = state["duration_seconds"]
        
        prompt = f"""Create a {duration}-second video ad script for: {state['product_name']}

Product Details:
- Category: {product_info.get('product_category', 'Unknown')}
- Description: {product_info.get('product_description', 'A premium product')}
- Key Features: {product_info.get('structure', {}).get('distinctive_features', [])}
- Visual Style: {product_info.get('materials', {}).get('surface_finish', 'professional')}

Target Audience: {state.get('target_audience', 'General consumers')}
Video Style: {state.get('video_style', 'Professional product showcase')}
Trending Hooks to Consider: {hooks[:3]}

Generate:
1. A compelling script with timestamps
2. A storyboard (list of shots with descriptions)
3. Voiceover text

Return as JSON:
{{
    "script": "Full script with [00:00] timestamps",
    "storyboard": [
        {{"shot_number": 1, "timestamp": "00:00-00:03", "description": "...", "camera": "...", "motion": "..."}}
    ],
    "voiceover": "Clean voiceover text without timestamps"
}}"""

        url = f"{self.azure_endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version=2024-02-15-preview"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                json={
                    "messages": [
                        {"role": "system", "content": "You are an expert video ad scriptwriter. Always return valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.7,
                },
                headers={
                    "Content-Type": "application/json",
                    "api-key": self.azure_api_key,
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Parse JSON from response
                try:
                    # Handle markdown code blocks
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {
                        "script": content,
                        "storyboard": [],
                        "voiceover": ""
                    }
        
        # Fallback
        return {
            "script": f"[00:00] Introducing {state['product_name']}...",
            "storyboard": [
                {"shot_number": 1, "timestamp": "00:00-00:05", "description": "Product reveal", "camera": "zoom_in", "motion": "slow"}
            ],
            "voiceover": f"Discover the new {state['product_name']}."
        }


class MotionNode:
    """
    Motion Stage: 4D Depth Skeleton / Motion Scaffold generation.
    
    Creates temporal scaffolding before pixels to ensure
    zero-shot product consistency in video frames.
    """
    
    def __init__(self):
        self.azure_endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        self.azure_api_key = settings.AZURE_OPENAI_API_KEY
        self.deployment_name = settings.AZURE_DEPLOYMENT_NAME
    
    async def __call__(self, state: NexusState) -> NexusState:
        """Execute motion scaffold generation."""
        logger.info(f"🎬 Motion Stage - Job: {state['job_id']}")
        
        state["status"] = JobStatus.CREATING_MOTION.value
        state["current_stage"] = "motion"
        state["progress_percent"] = 55.0
        state["updated_at"] = utc_now_iso()
        state["stage_messages"] = [f"[{state['updated_at']}] Creating motion scaffold..."]
        
        try:
            # Get recommendations from product identity
            identity = state.get("product_identity") or {}
            motion_recs = identity.get("motion_recommendations", [])
            camera_suggestions = identity.get("camera_suggestions", [])
            storyboard = state.get("storyboard", [])
            
            # Generate motion scaffold
            scaffold = await self._generate_motion_scaffold(
                duration=state["duration_seconds"],
                storyboard=storyboard,
                motion_recommendations=motion_recs,
                camera_suggestions=camera_suggestions,
                aspect_ratio=state["aspect_ratio"]
            )
            
            state["motion_scaffold"] = scaffold
            state["camera_movements"] = scaffold.get("camera_movements", [])
            state["keyframes"] = scaffold.get("keyframes", [])
            
            state["progress_percent"] = 70.0
            state["stage_messages"] = [
                f"[{utc_now_iso()}] ✅ Motion scaffold created with {len(scaffold.get('keyframes', []))} keyframes"
            ]
            
        except Exception as e:
            logger.error(f"Motion generation failed: {e}")
            state["errors"] = [f"Motion stage failed: {str(e)}"]
            # Continue with basic scaffold
            state["motion_scaffold"] = self._create_basic_scaffold(state["duration_seconds"])
        
        return state
    
    async def _generate_motion_scaffold(
        self,
        duration: float,
        storyboard: List[Dict],
        motion_recommendations: List[str],
        camera_suggestions: List[str],
        aspect_ratio: str
    ) -> Dict[str, Any]:
        """Generate detailed motion scaffold using GPT-4o."""
        
        fps = 24
        total_frames = int(duration * fps)
        
        prompt = f"""Create a motion scaffold for a {duration}-second video ad.

Storyboard:
{json.dumps(storyboard, indent=2)}

Motion Recommendations: {motion_recommendations}
Camera Suggestions: {camera_suggestions}
Aspect Ratio: {aspect_ratio}
FPS: {fps}
Total Frames: {total_frames}

Generate a motion scaffold with:
1. Keyframes at important transition points
2. Camera movements for each segment
3. Object motion paths
4. Easing curves

Return JSON:
{{
    "fps": {fps},
    "total_frames": {total_frames},
    "duration_seconds": {duration},
    "keyframes": [
        {{
            "frame": 0,
            "timestamp": 0.0,
            "camera": {{"position": [0,0,5], "rotation": [0,0,0], "fov": 50}},
            "product_transform": {{"position": [0,0,0], "rotation": [0,0,0], "scale": 1.0}},
            "easing": "ease_in_out"
        }}
    ],
    "camera_movements": [
        {{"start_frame": 0, "end_frame": 72, "type": "dolly_zoom", "intensity": 0.5}}
    ],
    "motion_paths": [
        {{"object": "product", "path_type": "orbit", "start_frame": 0, "end_frame": 120}}
    ]
}}"""

        url = f"{self.azure_endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version=2024-02-15-preview"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                json={
                    "messages": [
                        {"role": "system", "content": "You are a motion graphics expert. Return valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.3,
                },
                headers={
                    "Content-Type": "application/json",
                    "api-key": self.azure_api_key,
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                try:
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass
        
        return self._create_basic_scaffold(duration)
    
    def _create_basic_scaffold(self, duration: float) -> Dict[str, Any]:
        """Create a basic motion scaffold as fallback."""
        fps = 24
        total_frames = int(duration * fps)
        
        return {
            "fps": fps,
            "total_frames": total_frames,
            "duration_seconds": duration,
            "keyframes": [
                {
                    "frame": 0,
                    "timestamp": 0.0,
                    "camera": {"position": [0, 0, 5], "rotation": [0, 0, 0], "fov": 50},
                    "product_transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": 1.0},
                    "easing": "ease_out"
                },
                {
                    "frame": total_frames // 2,
                    "timestamp": duration / 2,
                    "camera": {"position": [2, 1, 4], "rotation": [10, 45, 0], "fov": 45},
                    "product_transform": {"position": [0, 0, 0], "rotation": [0, 180, 0], "scale": 1.0},
                    "easing": "ease_in_out"
                },
                {
                    "frame": total_frames - 1,
                    "timestamp": duration,
                    "camera": {"position": [0, 0, 3], "rotation": [0, 0, 0], "fov": 55},
                    "product_transform": {"position": [0, 0, 0], "rotation": [0, 360, 0], "scale": 1.0},
                    "easing": "ease_in"
                }
            ],
            "camera_movements": [
                {"start_frame": 0, "end_frame": total_frames, "type": "orbit", "intensity": 0.3}
            ],
            "motion_paths": []
        }


class RenderNode:
    """
    Render Stage: Hybrid Neural Rendering.
    
    Uses NeuralRenderAgent with:
    - SkyReels-V2 (Replicate) for motion-scaffold video generation
    - Sora-2 (OpenAI) for high-fidelity refinement
    - Fallback image sequence generation
    """
    
    def __init__(self):
        from backend.app.agents.neural_render import (
            NeuralRenderAgent, 
            RenderRequest, 
            RenderBackend, 
            RenderQuality
        )
        self._render_agent = NeuralRenderAgent()
        self._RenderRequest = RenderRequest
        self._RenderBackend = RenderBackend
        self._RenderQuality = RenderQuality
    
    async def __call__(self, state: NexusState) -> NexusState:
        """Execute rendering stage."""
        logger.info(f"🎨 Render Stage - Job: {state['job_id']}")
        
        state["status"] = JobStatus.RENDERING.value
        state["current_stage"] = "render"
        state["progress_percent"] = 75.0
        state["updated_at"] = utc_now_iso()
        state["stage_messages"] = [f"[{state['updated_at']}] Starting neural rendering..."]
        
        try:
            # Build render request
            render_request = self._build_render_request(state)

            # NOTE: Keep real video generation capability integrated but disabled by default
            # to avoid consuming paid video credits in non-production environments.
            if not settings.VIDEO_GENERATION_ENABLED:
                state["render_settings"] = {
                    "status": "disabled",
                    "reason": "VIDEO_GENERATION_ENABLED is False",
                    "width": render_request.width,
                    "height": render_request.height,
                    "fps": render_request.fps,
                    "duration_seconds": render_request.duration_seconds,
                    "backend_requested": render_request.backend.value,
                }
                state["video_url"] = None
                state["thumbnail_url"] = None
                state["preview_frames"] = []
                state["progress_percent"] = 95.0
                state["stage_messages"] = [
                    f"[{utc_now_iso()}] ⏸️ Render skipped (video generation disabled)"
                ]
                return state
            
            state["progress_percent"] = 80.0
            state["stage_messages"] = [
                f"[{utc_now_iso()}] Render request configured"
            ]
            
            # Progress callback to update state
            async def update_progress(progress: float, message: str):
                # Scale progress from 80% to 95%
                scaled = 80.0 + (progress * 15.0)
                state["progress_percent"] = scaled
                state["stage_messages"] = [
                    f"[{utc_now_iso()}] {message}"
                ]
            
            # Execute render using NeuralRenderAgent
            render_result = await self._render_agent.render_video(
                render_request,
                progress_callback=update_progress
            )
            
            # Store render settings for reference
            state["render_settings"] = {
                "width": render_result.width,
                "height": render_result.height,
                "fps": render_result.fps,
                "duration_seconds": render_result.duration_seconds,
                "backend_used": render_result.backend_used.value,
                "generation_time_seconds": render_result.generation_time_seconds,
                "seed_used": render_result.seed_used,
            }
            
            # Store output URLs
            state["video_url"] = render_result.output_url or render_result.output_path
            state["thumbnail_url"] = render_result.thumbnail_url
            state["preview_frames"] = [
                render_result.preview_gif_url or render_result.thumbnail_url
            ] if render_result.thumbnail_url else []
            
            state["progress_percent"] = 95.0
            state["stage_messages"] = [
                f"[{utc_now_iso()}] ✅ Render complete ({render_result.backend_used.value})"
            ]
            
        except Exception as e:
            logger.error(f"Rendering failed: {e}")
            state["errors"] = [f"Render stage failed: {str(e)}"]
            state["should_continue"] = False
        
        return state
    
    def _build_render_request(self, state: NexusState):
        """Build RenderRequest from orchestrator state."""
        
        # Parse aspect ratio
        aspect_parts = state["aspect_ratio"].split(":")
        width_ratio = int(aspect_parts[0])
        height_ratio = int(aspect_parts[1])
        
        # Calculate resolution (1080p base)
        if width_ratio > height_ratio:
            width = 1920
            height = int(1920 * height_ratio / width_ratio)
        else:
            height = 1080
            width = int(1080 * width_ratio / height_ratio)
        
        # Construct prompt from script
        script = state.get("script") or {}
        prompt_parts = []
        
        # Add main visual description
        if isinstance(script, dict):
            for scene in script.get("scenes", []):
                if isinstance(scene, dict) and scene.get("visual_description"):
                    prompt_parts.append(scene["visual_description"])
        elif isinstance(script, str) and script.strip():
            # Backward compatibility: older flows/tests may provide plain script text
            prompt_parts.append(script.strip()[:400])
        
        # Fallback to basic prompt
        if not prompt_parts:
            product = state.get("product_identity") or {}
            product_name = product.get("name", "Product")
            prompt_parts.append(
                f"Professional product video showcasing {product_name}, "
                f"studio lighting, premium quality, marketing video"
            )
        
        prompt = " ".join(prompt_parts[:2])  # Use first 2 scene descriptions
        
        # Get motion scaffold
        motion_scaffold = state.get("motion_scaffold")
        
        # Get identity embedding for product consistency
        identity_embedding = None
        product_identity = state.get("product_identity") or {}
        if product_identity:
            identity_embedding = product_identity.get("embedding")
        
        # Map quality setting
        quality_map = {
            "preview": self._RenderQuality.PREVIEW,
            "draft": self._RenderQuality.DRAFT,
            "standard": self._RenderQuality.STANDARD,
            "high": self._RenderQuality.HIGH,
            "ultra": self._RenderQuality.ULTRA,
        }
        quality_str = state.get("quality", "standard").lower()
        quality = quality_map.get(quality_str, self._RenderQuality.STANDARD)
        
        return self._RenderRequest(
            prompt=prompt,
            negative_prompt="blurry, distorted, low quality, amateur, shaky",
            width=width,
            height=height,
            backend=self._RenderBackend.SKIREELS_V2,  # Default to SkyReels
            quality=quality,
            duration_seconds=state["duration_seconds"],
            fps=motion_scaffold.get("fps", 24) if motion_scaffold else 24,
            motion_scaffold=motion_scaffold,
            identity_embedding=identity_embedding,
            seed=state.get("seed"),
        )

    def _build_render_settings(self, state: NexusState) -> Dict[str, Any]:
        """Backward-compatible helper for tests/tools expecting render settings dict."""
        render_request = self._build_render_request(state)
        return {
            "width": render_request.width,
            "height": render_request.height,
            "fps": render_request.fps,
            "duration_seconds": render_request.duration_seconds,
            "backend_requested": render_request.backend.value,
        }


class FinalizeNode:
    """
    Finalization Stage: Compile results and cleanup.
    """
    
    async def __call__(self, state: NexusState) -> NexusState:
        """Finalize the workflow."""
        logger.info(f"✅ Finalize Stage - Job: {state['job_id']}")
        
        state["current_stage"] = "complete"
        state["progress_percent"] = 100.0
        state["updated_at"] = utc_now_iso()
        
        if state["errors"]:
            state["status"] = JobStatus.FAILED.value
            state["stage_messages"] = [
                f"[{state['updated_at']}] ❌ Job completed with {len(state['errors'])} error(s)"
            ]
        else:
            state["status"] = JobStatus.COMPLETED.value
            state["stage_messages"] = [
                f"[{state['updated_at']}] 🎉 Job completed successfully!"
            ]
        
        state["should_continue"] = False
        
        return state


# =============================================================================
# ROUTING FUNCTIONS
# =============================================================================

def route_after_research(state: NexusState) -> str:
    """Route after research stage based on workflow type."""
    if not state["should_continue"]:
        return "finalize"
    
    workflow = state["workflow_type"]
    
    if workflow == WorkflowType.CONTENT_ONLY.value:
        return "content"
    elif workflow in [WorkflowType.PRODUCT_VIDEO.value, WorkflowType.FULL_PIPELINE.value]:
        return "content"
    else:
        return "content"


def route_after_content(state: NexusState) -> str:
    """Route after content stage."""
    if not state["should_continue"]:
        return "finalize"
    
    workflow = state["workflow_type"]
    
    if workflow == WorkflowType.CONTENT_ONLY.value:
        return "finalize"
    elif workflow == WorkflowType.IDENTITY_EXTRACTION.value:
        return "finalize"
    else:
        return "motion"


def route_after_motion(state: NexusState) -> str:
    """Route after motion stage."""
    if not state["should_continue"]:
        return "finalize"
    
    workflow = state["workflow_type"]
    
    if workflow == WorkflowType.MOTION_ONLY.value:
        return "finalize"
    else:
        return "render"


def route_after_render(state: NexusState) -> str:
    """Route after render stage."""
    if state.get("auto_publish"):
        return "publish"
    return "finalize"


# =============================================================================
# ORCHESTRATOR CLASS
# =============================================================================

class NexusOrchestrator:
    """
    The Catalyst Nexus Orchestrator - LangGraph State Machine.
    
    Coordinates the full video generation pipeline:
    
        Research → Content → Motion → Render → Finalize
    
    Features:
    - Stateful execution with checkpoints
    - Dynamic routing based on workflow type
    - Error recovery and retry logic
    - Progress tracking
    - Human-in-the-loop approval gates (optional)
    
    Usage:
        orchestrator = NexusOrchestrator()
        
        # Start a job
        result = await orchestrator.run(
            workflow_type="product_video",
            project_id="...",
            product_name="Premium Headphones",
            product_images=["https://..."],
            duration_seconds=15.0
        )
        
        # Check status
        status = orchestrator.get_status(job_id)
    """
    
    def __init__(self):
        """Initialize the orchestrator and build the workflow graph."""
        self.memory = MemorySaver()
        self.graph = self._build_graph()
        self._active_jobs: Dict[str, NexusState] = {}
        
        logger.info("🚀 Nexus Orchestrator initialized")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Create the graph
        workflow = StateGraph(NexusState)
        
        # Add nodes
        workflow.add_node("research", ResearchNode())
        workflow.add_node("content", ContentNode())
        workflow.add_node("motion", MotionNode())
        workflow.add_node("render", RenderNode())
        workflow.add_node("publish", PublishNode())
        workflow.add_node("finalize", FinalizeNode())
        
        # Set entry point
        workflow.set_entry_point("research")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "research",
            route_after_research,
            {
                "content": "content",
                "finalize": "finalize"
            }
        )
        
        workflow.add_conditional_edges(
            "content",
            route_after_content,
            {
                "motion": "motion",
                "finalize": "finalize"
            }
        )
        
        workflow.add_conditional_edges(
            "motion",
            route_after_motion,
            {
                "render": "render",
                "finalize": "finalize"
            }
        )
        
        workflow.add_conditional_edges(
            "render",
            route_after_render,
            {
                "publish": "publish",
                "finalize": "finalize"
            }
        )

        workflow.add_edge("publish", "finalize")
        
        # Finalize always ends
        workflow.add_edge("finalize", END)
        
        # Compile with checkpointer
        return workflow.compile(checkpointer=self.memory)
    
    async def run(
        self,
        workflow_type: str,
        project_id: str,
        product_name: str,
        product_images: List[str],
        duration_seconds: float = 15.0,
        aspect_ratio: str = "16:9",
        job_id: Optional[str] = None,
        **kwargs
    ) -> NexusState:
        """
        Run a video generation workflow.
        
        Args:
            workflow_type: Type of workflow (product_video, identity_extraction, etc.)
            project_id: Project UUID
            product_name: Name of the product
            product_images: List of product image URLs
            duration_seconds: Target video duration
            aspect_ratio: Video aspect ratio (16:9, 9:16, 1:1)
            job_id: Optional custom job ID
            **kwargs: Additional parameters (brand_guidelines, target_audience, etc.)
            
        Returns:
            Final workflow state with all outputs
        """
        # Generate job ID if not provided
        job_id = job_id or str(uuid4())
        
        logger.info(f"🎬 Starting workflow: {workflow_type} (Job: {job_id})")
        
        # Create initial state
        initial_state = create_initial_state(
            job_id=job_id,
            workflow_type=workflow_type,
            project_id=project_id,
            product_name=product_name,
            product_images=product_images,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
            **kwargs
        )
        
        # Store in active jobs
        self._active_jobs[job_id] = initial_state
        
        # Configure thread for checkpointing
        config = {"configurable": {"thread_id": job_id}}
        
        try:
            # Execute the workflow
            final_state = await self.graph.ainvoke(initial_state, config)
            
            # Update active jobs
            self._active_jobs[job_id] = final_state
            
            logger.info(f"✅ Workflow complete: {job_id} (Status: {final_state['status']})")
            
            return final_state
            
        except Exception as e:
            logger.error(f"❌ Workflow failed: {job_id} - {str(e)}")
            
            error_state = {
                **initial_state,
                "status": JobStatus.FAILED.value,
                "errors": [f"Workflow execution failed: {str(e)}"],
                "progress_percent": 100.0,
                "should_continue": False,
            }
            
            self._active_jobs[job_id] = error_state
            return error_state
    
    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a job.
        
        Args:
            job_id: The job identifier
            
        Returns:
            Current state or None if not found
        """
        state = self._active_jobs.get(job_id)
        
        if state:
            return {
                "job_id": state["job_id"],
                "status": state["status"],
                "current_stage": state["current_stage"],
                "progress_percent": state["progress_percent"],
                "stage_messages": state["stage_messages"][-5:],  # Last 5 messages
                "errors": state["errors"],
                "video_url": state.get("video_url"),
                "thumbnail_url": state.get("thumbnail_url"),
            }
        
        return None
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all tracked jobs with basic info."""
        return [
            {
                "job_id": state["job_id"],
                "workflow_type": state["workflow_type"],
                "status": state["status"],
                "progress_percent": state["progress_percent"],
                "created_at": state["created_at"],
            }
            for state in self._active_jobs.values()
        ]
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.
        
        Args:
            job_id: The job to cancel
            
        Returns:
            True if cancelled, False if not found
        """
        if job_id in self._active_jobs:
            self._active_jobs[job_id]["status"] = JobStatus.CANCELLED.value
            self._active_jobs[job_id]["should_continue"] = False
            self._active_jobs[job_id]["stage_messages"].append(
                f"[{utc_now_iso()}] Job cancelled by user"
            )
            logger.info(f"🛑 Job cancelled: {job_id}")
            return True
        
        return False


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

_orchestrator_instance: Optional[NexusOrchestrator] = None


def get_orchestrator() -> NexusOrchestrator:
    """Get or create the singleton orchestrator instance."""
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        _orchestrator_instance = NexusOrchestrator()
    
    return _orchestrator_instance
