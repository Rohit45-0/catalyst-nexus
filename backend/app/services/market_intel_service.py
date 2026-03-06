
import logging
import json
import re
import asyncio
from collections import Counter
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.services.social_scraper import SocialScraperService
from backend.app.services.firecrawl_service import search_web as firecrawl_search
from backend.app.db.schemas import (
    AssistantChatResponse,
    CategoryTrendAnalysisResponse,
    CampaignGenerationResponse,
    GapAnalysisResult,
    ProductCampaignBriefRequest,
    TrendPostInsight,
)

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except Exception:  # pragma: no cover - optional dependency runtime guard
    YouTubeTranscriptApi = None

logger = logging.getLogger(__name__)

class MarketIntelService:
    """
    Service for Market Intelligence using Social Scraping and LLM Analysis.
    """
    
    ANALYSIS_PROMPT = """You are a Market Intelligence Analyst. Your goal is to find "Audience Gaps" in competitor content.
    
    I will provide you with a list of social media posts and their top comments from a competitor profile.
    
    Analyze the comments deeply to find:
    1. Unanswered Questions: What are users asking that the content creator didn't answer?
    2. Complaints/Frustrations: What are users annoyed about regarding the topic/product?
    3. Viral Hooks: What specific phrases or topics in the comments triggered high engagement?
    4. Opportunity Gap: What connects these points? What is the "Missing Content" that nobody is making?
    
    Input Data:
    {competitor_data}
    
    Output JSON format:
    {{
        "top_questions": ["question 1", "question 2", ...],
        "complaints": ["complaint 1", "complaint 2", ...],
        "viral_hooks": ["hook 1", "hook 2", ...],
        "opportunity_gap": "A 1-2 sentence description of the content opportunity gap."
    }}
    """
    
    def __init__(self):
        self.scraper = SocialScraperService()
        self.azure_endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
        self.api_key = settings.AZURE_OPENAI_API_KEY
        self.deployment_name = settings.AZURE_DEPLOYMENT_NAME
        self.youtube_api_key = settings.YOUTUBE_API_KEY
        self.brave_api_key = settings.BRAVE_API_KEY
        self.transcript_client = YouTubeTranscriptApi() if YouTubeTranscriptApi else None
        self.api_version = "2024-02-15-preview"
        
    async def analyze_competitor(self, username: str) -> GapAnalysisResult:
        """
        Full pipeline: Scrape profile -> Analyze -> Return Gaps
        """
        logger.info(f"Starting analysis for competitor: {username}")
        
        # 1. Scrape Data (carefully limited)
        intel_data = await self.scraper.get_competitor_intel(username)
        
        if not intel_data["posts"]:
            # Fallback: Try Firecrawl Web Search if social scraping fails
            logger.info(f"Social scraping empty for {username}, trying Firecrawl...")
            web_insights = await self._fetch_firecrawl_trends(f"{username} marketing strategy reviews", "US", 5)
            
            if not web_insights and self.brave_api_key:
                logger.info(f"Firecrawl empty for {username}, trying Brave...")
                web_insights = await self._fetch_brave_web_trends(f"{username} marketing strategy reviews", "US", 5)
            
            if web_insights:
                context_str = f"Competitor Analysis for {username} (Web Source):\n"
                for item in web_insights:
                    context_str += f"- {item.title}: {item.caption}\n"
                
                analysis_json = await self._call_llm_analysis(context_str)
                return GapAnalysisResult(
                    competitor=username,
                    top_questions=analysis_json.get("top_questions", []),
                    complaints=analysis_json.get("complaints", []),
                    viral_hooks=analysis_json.get("viral_hooks", []),
                    opportunity_gap=analysis_json.get("opportunity_gap", "Analysis derived from web search.")
                )

            logger.warning(f"No posts/web data found for {username}")
            return GapAnalysisResult(
                competitor=username,
                top_questions=[],
                complaints=[],
                viral_hooks=[],
                opportunity_gap="No data available to analyze (Instaloader 429'd, Firecrawl timed out, and Brave failed)."
            )
            
        # 2. Prepare context for LLM
        # Compress the text to save tokens
        context_str = f"Competitor: {username}\n"
        for post in intel_data["posts"]:
            caption = (post.get("caption") or "")[:200]
            context_str += f"\nPost Caption: {caption}\n"
            context_str += f"Likes: {post.get('likesCount')}, Comments: {post.get('commentsCount')}\n"
            context_str += "Top Comments:\n"
            for comment in post.get("comments_data", []):
                cleaned_text = (comment.get("text") or "").replace("\n", " ")
                context_str += f"- {cleaned_text}\n"
        
        # 3. Call LLM for Analysis
        analysis_json = await self._call_llm_analysis(context_str)
        
        # 4. Map to Result
        return GapAnalysisResult(
            competitor=username,
            top_questions=analysis_json.get("top_questions", []),
            complaints=analysis_json.get("complaints", []),
            viral_hooks=analysis_json.get("viral_hooks", []),
            opportunity_gap=analysis_json.get("opportunity_gap", "Analysis failed.")
        )

    async def analyze_category(self, category: str) -> Dict[str, Any]:
        """
        Niche-level intelligence: Scrape trending hashtags for a category.
        """
        category_map = {
            "Tech": ["techreview", "gadgetlife"],
            "Fashion": ["ootd", "fashionstyle"],
            "Finance": ["investing", "stockmarket"],
            "General": ["viral", "trending"]
        }
        
        hashtags = category_map.get(category, ["trending"])
        all_posts = []
        
        for hashtag in hashtags:
            posts = await self.scraper.scrape_hashtag(hashtag, max_posts=3)
            all_posts.extend(posts)
            
        if not all_posts:
            return {"error": f"No posts found for category {category}"}
            
        # Analyze top posts in category
        context_str = f"Category: {category}\n"
        for post in all_posts[:5]:
             # Fetch comments for hashtag posts to find gaps
             post_obj = post.pop("_post_obj", None)
             comments = await self.scraper.scrape_instagram_comments(post_obj, max_comments=5) if post_obj else []
             
             caption = (post.get("caption") or "")[:150]
             context_str += f"\nViral Post: {caption}\n"
             context_str += "Top Comments:\n"
             for comment in comments:
                 context_str += f"- {comment.get('text')}\n"
                 
        analysis = await self._call_llm_analysis(context_str)
        return {
            "category": category,
            "hashtag_trends": hashtags,
            "analysis": analysis
        }

    async def analyze_category_trends(
        self,
        category: str,
        platform: str = "youtube",
        region_code: str = "IN",
        max_results: int = 10,
    ) -> CategoryTrendAnalysisResponse:
        """Analyze category trends using API-first approach (YouTube first, Instagram fallback)."""
        platform = platform.lower().strip()
        region_code = region_code.upper().strip()

        if platform == "youtube":
            top_posts = await self._fetch_youtube_trending_by_category(
                category=category,
                region_code=region_code,
                max_results=max_results,
            )
            data_source = "youtube_data_api"

            if not top_posts:
                # 1. Try Firecrawl (Deep Web Search)
                top_posts = await self._fetch_firecrawl_trends(
                    category=category,
                    region_code=region_code,
                    max_results=max_results,
                )
                if top_posts:
                    data_source = "firecrawl_search"

            if not top_posts and self.brave_api_key:
                # 2. Fallback to Brave
                top_posts = await self._fetch_brave_web_trends(
                    category=category,
                    region_code=region_code,
                    max_results=max_results,
                )
                if top_posts:
                    data_source = "brave_search_api"

            if not top_posts and not self.youtube_api_key:
                data_source = "heuristic_fallback"
        else:
            top_posts = await self._fetch_instagram_category_posts(category, max_results=max_results)
            data_source = "instaloader"

            if not top_posts:
                # 1. Try Firecrawl
                top_posts = await self._fetch_firecrawl_trends(
                    category=category,
                    region_code=region_code,
                    max_results=max_results,
                )
                if top_posts:
                    data_source = "firecrawl_search"

            if not top_posts and self.brave_api_key:
                # 2. Fallback to Brave
                top_posts = await self._fetch_brave_web_trends(
                    category=category,
                    region_code=region_code,
                    max_results=max_results,
                )
                if top_posts:
                    data_source = "brave_search_api"

        if not top_posts:
            return CategoryTrendAnalysisResponse(
                category=category,
                platform=platform,
                region_code=region_code,
                data_source=data_source,
                top_posts=[],
                top_keywords=[],
                recommended_hooks=[
                    "Lead with one bold pain-point in first 2 seconds",
                    "Show clear before/after transformation quickly",
                ],
                content_gaps=[
                    "No recent high-performing posts found; start with problem-solution educational format"
                ],
                posting_recommendations=[
                    "Test 2 posting slots daily for 7 days and keep the top performer",
                ],
                generated_at=datetime.utcnow(),
            )

        top_keywords = self._extract_keywords([p.title for p in top_posts], limit=12)
        top_posts = self._rank_posts(top_posts)[:max_results]

        return CategoryTrendAnalysisResponse(
            category=category,
            platform=platform,
            region_code=region_code,
            data_source=data_source,
            top_posts=top_posts,
            top_keywords=top_keywords,
            recommended_hooks=self._build_hooks_from_keywords(category, top_keywords),
            content_gaps=self._derive_content_gaps(top_keywords, category),
            posting_recommendations=self._derive_posting_recommendations(top_posts),
            generated_at=datetime.utcnow(),
        )

    async def generate_campaign_from_product(
        self,
        request: ProductCampaignBriefRequest,
    ) -> CampaignGenerationResponse:
        """Generate cross-format campaign ideas based on trend analysis + product context.

        video_generation_enabled=False  → posters + blogs + reels (ideas) + tweets only.
        video_generation_enabled=True   → all of the above + short_video_ideas (production scripts)
                                          AND _generate_video_asset() will actually call Seedance.
        """
        preferred_platform = "youtube"

        trend_analysis = await self.analyze_category_trends(
            category=request.category,
            platform=preferred_platform,
            region_code=request.region_code,
            max_results=10,
        )

        # ── LLM prompt payload ────────────────────────────────────────────────
        llm_payload = {
            "product_name": request.product_name,
            "product_description": request.product_description,
            "target_audience": request.target_audience,
            "category": request.category,
            "product_image_url": request.product_image_url,
            "product_image_name": request.product_image_name,
            "identity_notes": request.identity_notes,
            "trend_keywords": trend_analysis.top_keywords,
            "trend_hooks": trend_analysis.recommended_hooks,
            "content_gaps": trend_analysis.content_gaps,
        }

        # ── INJECT VISUAL DNA ─────────────────────────────────────────────────
        # This gives the LLM the actual visual identity of the product
        # (colors, materials, shape, distinctive features) extracted from the image.
        if request.visual_dna:
            dna = request.visual_dna
            materials = dna.get("materials", {})
            structure = dna.get("structure", {})
            llm_payload["product_visual_identity"] = {
                "color_palette": materials.get("color_palette", []),
                "primary_material": materials.get("primary_material", ""),
                "surface_finish": materials.get("surface_finish", ""),
                "product_shape": structure.get("overall_shape", ""),
                "distinctive_features": structure.get("distinctive_features", []),
                "brand_elements": structure.get("brand_elements", []),
                "camera_angles": dna.get("camera_angle_suggestions", []),
                "motion_recommendations": dna.get("motion_recommendations", []),
            }

        # ── INJECT COMPETITOR INSIGHTS ────────────────────────────────────────
        # This gives the LLM the competitive gaps and viral hooks from
        # real competitor analysis — so it can target unmet audience needs.
        if request.competitor_insights:
            llm_payload["competitor_analysis"] = {
                "gaps_to_exploit": [
                    c.get("opportunity_gap", "") for c in request.competitor_insights
                    if c.get("opportunity_gap")
                ],
                "viral_hooks_from_competitors": [
                    hook for c in request.competitor_insights
                    for hook in (c.get("viral_hooks") or [])
                ][:8],
                "audience_questions_unanswered": [
                    q for c in request.competitor_insights
                    for q in (c.get("top_questions") or [])
                ][:8],
            }

        if request.video_generation_enabled:
            # Signal GPT to include production-ready video scripts
            llm_payload["video_mode"] = (
                "ON — include 5 short_video_ideas as production-ready scripts "
                "(motion prompt, voiceover hook, visual style) ready for AI video rendering."
            )

        transcript_insights = await self._build_transcript_insights(trend_analysis.top_posts)
        if transcript_insights:
            llm_payload["transcript_insights"] = transcript_insights

        llm_result = await self._generate_campaign_ideas_with_llm(
            llm_payload, include_video=request.video_generation_enabled, system_prompt=request.system_prompt
        )

        fallback_strategy = (
            f"Position {request.product_name} as the fastest path to outcomes for "
            f"{request.target_audience} in {request.category}."
        )

        campaign_strategy = self._normalize_campaign_strategy(
            llm_result.get("campaign_strategy"),
            default=fallback_strategy,
        )

        strategy = campaign_strategy
        if request.product_image_name or request.product_image_url:
            strategy = (
                f"{strategy}\n\nIdentity context: Product image attached"
                f" ({request.product_image_name or 'unnamed image'})"
                f"{' with hosted URL' if request.product_image_url else ''}."
            )

        return CampaignGenerationResponse(
            category_trend_analysis=trend_analysis,
            campaign_strategy=strategy,
            blog_ideas=self._normalize_ideas(llm_result.get("blog_ideas"), self._fallback_blog_ideas(request)),
            tweet_ideas=self._normalize_ideas(llm_result.get("tweet_ideas"), self._fallback_tweet_ideas(request)),
            reel_ideas=self._normalize_ideas(llm_result.get("reel_ideas"), self._fallback_reel_ideas(request)),
            # short_video_ideas only populated when video toggle is ON
            short_video_ideas=(
                self._normalize_ideas(llm_result.get("short_video_ideas"), self._fallback_short_ideas(request))
                if request.video_generation_enabled
                else []
            ),
            poster_ideas=self._normalize_ideas(llm_result.get("poster_ideas"), self._fallback_poster_ideas(request)),
        )

    async def assistant_chat(
        self,
        message: str,
        history: List[Dict[str, str]],
        context: Dict[str, Any],
        video_generation_enabled: bool = False,
        user_id: Optional[UUID] = None,
        db: Optional[Session] = None,
    ) -> AssistantChatResponse:
        """Conversational assistant for campaign planning with memory from provided history/context & RAG."""
        
        # ── Pull from RAG Memory ──────────────────────────────────────────────
        past_knowledge_text = ""
        if user_id and db:
            try:
                from backend.app.services.rag_service import get_rag_service
                rag = get_rag_service(db)
                past_knowledge = await rag.search(query=message, user_id=user_id, limit=3)
                if past_knowledge:
                    past_knowledge_text = "\n".join([f"• {k.content}" for k in past_knowledge])
            except Exception as e:
                logger.warning(f"Failed to fetch RAG memory for assistant chat: {e}")

        prompt = {
            "message": message,
            "history": history[-12:],
            "context": context,
            "video_generation_enabled": video_generation_enabled,
            "user_history_knowledge": past_knowledge_text,  # Injecting the magic!
            "instruction": (
                "Respond as Catalyst Nexus copilot. Be tactical, concise, and interactive. "
                "Ask one clarifying follow-up question when needed. If user asks for ideas, provide numbered actionable options. "
                "Use the 'user_history_knowledge' to reference their past campaigns if relevant."
            ),
        }
        url = f"{self.azure_endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
        payload = {
            "messages": [
                {"role": "system", "content": "You are Catalyst Nexus AI marketing assistant."},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            "max_tokens": 500,
            "temperature": 0.7,
        }
        headers = {"Content-Type": "application/json", "api-key": self.api_key}
        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return AssistantChatResponse(reply=content.strip())
            except Exception as e:
                logger.error(f"Assistant chat failed: {e}")
                suffix = " Video generation is currently ON." if video_generation_enabled else " Video generation is OFF."
                return AssistantChatResponse(
                    reply=(
                        "I couldn't reach the live assistant model right now. "
                        "Try this next: share your campaign objective, target audience, and budget, and I will generate a precise plan." + suffix
                    )
                )

    async def generate_system_prompt(self, category: str, product_name: Optional[str] = None) -> str:
        """Generate a highly tailored system prompt for campaign generation based on the category."""
        target = f"{product_name} in the {category} category" if product_name else f"the {category} category"
        prompt = (
            f"You are an expert Marketing Director and Master Prompt Engineer. "
            f"The user is creating a marketing campaign for a product: {target}.\n\n"
            f"Write a comprehensive System Prompt that will be given to a Campaign Generator AI. "
            f"The prompt MUST instruct the AI on the optimal tone of voice, psychological triggers, "
            f"industry-specific vocabulary, and content formats to use for {category}.\n\n"
            f"Just return the system prompt directly, do not include any preamble."
        )

        url = f"{self.azure_endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
        payload = {
            "messages": [
                {"role": "system", "content": "You are an expert meta-prompt engineer."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 800,
            "temperature": 0.7,
        }
        headers = {"Content-Type": "application/json", "api-key": self.api_key}
        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return content.strip()
            except Exception as e:
                logger.error(f"System prompt generation failed: {e}")
                return "You are an elite performance marketing strategist. Keep ideas specific and actionable."


    async def _build_transcript_insights(self, posts: List[TrendPostInsight], max_videos: int = 5) -> Dict[str, Any]:
        """Fetch and summarize transcript patterns from top YouTube videos."""
        youtube_posts = [p for p in posts if p.platform == "youtube" and p.post_id][:max_videos]
        if not youtube_posts or not self.transcript_client:
            return {}

        transcripts: List[Dict[str, Any]] = []
        for post in youtube_posts:
            entry = await self._fetch_single_transcript(post.post_id)
            if entry:
                entry["video_id"] = post.post_id
                entry["title"] = post.title
                transcripts.append(entry)

        if not transcripts:
            return {}

        hooks = [t.get("hook_line", "") for t in transcripts if t.get("hook_line")]
        ctas = [t.get("cta_line", "") for t in transcripts if t.get("cta_line")]
        phrases = []
        for t in transcripts:
            phrases.extend(t.get("top_phrases", []))

        phrase_counts = Counter([p.strip().lower() for p in phrases if p and p.strip()])
        common_phrases = [p for p, _ in phrase_counts.most_common(12)]

        return {
            "video_count": len(transcripts),
            "sampled_videos": [{"video_id": t.get("video_id"), "title": t.get("title")} for t in transcripts],
            "common_hook_lines": hooks[:10],
            "common_cta_lines": ctas[:10],
            "common_phrases": common_phrases,
        }

    async def _fetch_single_transcript(self, video_id: str) -> Dict[str, Any]:
        """Fetch transcript for a single YouTube video using youtube-transcript-api."""
        if not self.transcript_client:
            return {}

        def _fetch() -> Dict[str, Any]:
            try:
                fetched = self.transcript_client.fetch(video_id, languages=["en", "en-IN", "hi"])
                raw_items = fetched.to_raw_data() if fetched else []
                lines = [str(item.get("text", "")).strip() for item in raw_items if item.get("text")]
                lines = [ln for ln in lines if ln]
                if not lines:
                    return {}

                hook_line = lines[0][:180]
                cta_line = ""
                for ln in reversed(lines[-12:]):
                    low = ln.lower()
                    if any(k in low for k in ["subscribe", "buy", "link", "comment", "follow", "shop"]):
                        cta_line = ln[:180]
                        break

                text_blob = " ".join(lines[:120])
                top_phrases = self._extract_phrases(text_blob, limit=8)
                return {
                    "hook_line": hook_line,
                    "cta_line": cta_line,
                    "top_phrases": top_phrases,
                }
            except Exception:
                return {}

        return await asyncio.to_thread(_fetch)

    def _extract_phrases(self, text: str, limit: int = 8) -> List[str]:
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9']{2,}", text.lower())
        stop_words = {
            "the", "and", "for", "with", "this", "that", "your", "from", "how", "why", "what",
            "you", "are", "was", "were", "have", "has", "had", "not", "but", "all", "can",
        }
        filtered = [t for t in tokens if t not in stop_words]
        if len(filtered) < 2:
            return []

        bigrams = [f"{filtered[i]} {filtered[i+1]}" for i in range(len(filtered) - 1)]
        counts = Counter(bigrams)
        return [phrase for phrase, _ in counts.most_common(limit)]

    async def _fetch_youtube_trending_by_category(
        self,
        category: str,
        region_code: str,
        max_results: int,
    ) -> List[TrendPostInsight]:
        """Fetch trending videos from YouTube Data API using search + stats enrichment."""
        if not self.youtube_api_key:
            logger.warning("YOUTUBE_API_KEY not configured. Returning empty trend data.")
            return []

        search_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": category,
            "type": "video",
            "order": "viewCount",
            "regionCode": region_code,
            "maxResults": min(max_results, 50),
            "key": self.youtube_api_key,
        }

        async with httpx.AsyncClient(timeout=40.0) as client:
            try:
                search_resp = await client.get(search_url, params=params)
                search_resp.raise_for_status()
                search_data = search_resp.json().get("items", [])

                video_ids = [item.get("id", {}).get("videoId") for item in search_data if item.get("id", {}).get("videoId")]
                if not video_ids:
                    return []

                stats_url = "https://www.googleapis.com/youtube/v3/videos"
                stats_resp = await client.get(
                    stats_url,
                    params={
                        "part": "statistics,snippet",
                        "id": ",".join(video_ids),
                        "key": self.youtube_api_key,
                    },
                )
                stats_resp.raise_for_status()
                stats_map = {
                    item.get("id"): item for item in stats_resp.json().get("items", []) if item.get("id")
                }

                results: List[TrendPostInsight] = []
                for item in search_data:
                    vid = item.get("id", {}).get("videoId")
                    if not vid:
                        continue
                    stat_item = stats_map.get(vid, {})
                    statistics = stat_item.get("statistics", {})
                    snippet = stat_item.get("snippet", item.get("snippet", {}))

                    views = int(statistics.get("viewCount", 0) or 0)
                    likes = int(statistics.get("likeCount", 0) or 0)
                    comments = int(statistics.get("commentCount", 0) or 0)
                    engagement_rate = ((likes + comments) / views) if views > 0 else None

                    published_raw = snippet.get("publishedAt")
                    published_at = None
                    if published_raw:
                        try:
                            published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
                        except ValueError:
                            published_at = None

                    results.append(
                        TrendPostInsight(
                            platform="youtube",
                            post_id=vid,
                            title=snippet.get("title", "Untitled"),
                            url=f"https://www.youtube.com/watch?v={vid}",
                            author=snippet.get("channelTitle"),
                            published_at=published_at,
                            views=views,
                            likes=likes,
                            comments=comments,
                            engagement_rate=engagement_rate,
                        )
                    )
                return results
            except Exception as e:
                logger.error(f"YouTube trend fetch failed: {e}")
                return []

    async def _fetch_brave_web_trends(
        self,
        category: str,
        region_code: str,
        max_results: int,
    ) -> List[TrendPostInsight]:
        """Fetch category trend-like web/video results via Brave Search API."""
        if not self.brave_api_key:
            return []

        query = f"{category} trending videos best ads creators {region_code}"
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.brave_api_key,
        }
        params = {
            "q": query,
            "count": min(max_results, 20),
            "country": region_code,
            "search_lang": "en",
            "safesearch": "moderate",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                web_results = data.get("web", {}).get("results", [])

                insights: List[TrendPostInsight] = []
                for item in web_results:
                    title = (item.get("title") or "").strip()
                    page_url = (item.get("url") or "").strip()
                    if not title or not page_url:
                        continue

                    post_id = re.sub(r"[^a-zA-Z0-9]", "", page_url)[-24:] or "web_result"
                    desc = (item.get("description") or "").strip()
                    insights.append(
                        TrendPostInsight(
                            platform="web",
                            post_id=post_id,
                            title=title,
                            url=page_url,
                            author=(item.get("profile", {}).get("name") if isinstance(item.get("profile"), dict) else None),
                            published_at=None,
                            views=None,
                            likes=None,
                            comments=None,
                            engagement_rate=None,
                            caption=desc
                        )
                    )

                return insights[:max_results]
            except Exception as e:
                logger.error(f"Brave trend fetch failed: {e}")
                return []

    async def _fetch_firecrawl_trends(
        self,
        category: str,
        region_code: str,
        max_results: int,
    ) -> List[TrendPostInsight]:
        """Fetch category trends using Firecrawl (Deep Web Search)."""
        try:
            query = f"{category} market trends analysis {region_code} 2024"
            
            # Firecrawl is synchronous, run in threadpool with strict timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.to_thread(
                        firecrawl_search, 
                        query=query, 
                        limit=min(max_results, 8), 
                        scrape_content=False
                    ),
                    timeout=12.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Firecrawl search timed out for {category}, falling back to Brave.")
                return []
            
            insights: List[TrendPostInsight] = []
            for item in results:
                title = (item.get("title") or "").strip()
                url = (item.get("url") or "").strip()
                desc = (item.get("description") or "").strip()
                
                if not title or not url:
                    continue
                    
                post_id = re.sub(r"[^a-zA-Z0-9]", "", url)[-24:] or "fc_result"
                
                # Create a pseudo-post from the search result
                insights.append(
                    TrendPostInsight(
                        platform="web",
                        post_id=post_id,
                        title=title,
                        url=url,
                        author="Web Source",
                        published_at=None,
                        views=None,
                        likes=None,
                        comments=None,
                        engagement_rate=None,
                        caption=desc  # Use description as caption/context
                    )
                )
            logger.info(f"Firecrawl found {len(insights)} results for {category}")
            return insights
        except Exception as e:
            logger.warning(f"Firecrawl search failed: {e}")
            return []

    async def _fetch_instagram_category_posts(self, category: str, max_results: int) -> List[TrendPostInsight]:
        """Fallback category fetch using existing instaloader hashtags."""
        normalized = category.strip().lower().replace(" ", "")
        hashtags = [normalized, "trending", "viral"]
        collected: List[TrendPostInsight] = []

        for tag in hashtags:
            posts = await self.scraper.scrape_hashtag(tag, max_posts=max(3, max_results // 2))
            for post in posts:
                likes = int(post.get("likesCount", 0) or 0)
                comments = int(post.get("commentsCount", 0) or 0)
                engagement_rate = (comments / likes) if likes else None
                collected.append(
                    TrendPostInsight(
                        platform="instagram",
                        post_id=post.get("id", "unknown"),
                        title=(post.get("caption") or "").strip()[:120] or "Instagram post",
                        url=post.get("url", ""),
                        author=post.get("ownerUsername"),
                        published_at=None,
                        views=likes,
                        likes=likes,
                        comments=comments,
                        engagement_rate=engagement_rate,
                    )
                )
            if len(collected) >= max_results:
                break

        return collected[:max_results]

    def _extract_keywords(self, texts: List[str], limit: int = 10) -> List[str]:
        stop_words = {
            "the", "and", "for", "with", "this", "that", "your", "from", "how", "why", "what",
            "best", "video", "shorts", "reel", "reels", "you", "are", "new", "top", "in", "of",
        }
        tokens: List[str] = []
        for text in texts:
            words = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", text.lower())
            tokens.extend([w for w in words if w not in stop_words])

        counts = Counter(tokens)
        return [w for w, _ in counts.most_common(limit)]

    def _rank_posts(self, posts: List[TrendPostInsight]) -> List[TrendPostInsight]:
        return sorted(
            posts,
            key=lambda p: (
                p.views or 0,
                p.engagement_rate or 0,
                p.likes or 0,
                p.comments or 0,
            ),
            reverse=True,
        )

    def _build_hooks_from_keywords(self, category: str, keywords: List[str]) -> List[str]:
        k1 = keywords[0] if keywords else category
        k2 = keywords[1] if len(keywords) > 1 else "results"
        return [
            f"Stop wasting money on {category}: do this {k1} framework instead.",
            f"I tried 3 {category} tactics in 7 days — only this {k2} method worked.",
            f"Before you buy any {category} solution, check this 10-second test.",
        ]

    def _derive_content_gaps(self, keywords: List[str], category: str) -> List[str]:
        focus = keywords[:3] if keywords else [category]
        return [
            f"Few creators explain beginner mistakes around {', '.join(focus)}.",
            f"Lack of side-by-side competitor breakdowns in {category}.",
            "Not enough transparent pricing/value comparison content.",
        ]

    def _derive_posting_recommendations(self, posts: List[TrendPostInsight]) -> List[str]:
        rates = [p.engagement_rate for p in posts if p.engagement_rate is not None]
        avg_engagement = (sum(rates) / len(rates)) if rates else 0.0
        return [
            "Publish 4-6 short-form pieces per week with first-frame product proof.",
            f"Current benchmark engagement-rate from sampled trends: {avg_engagement:.2%}.",
            "Test hooks in first 2 seconds and retain winning variants for paid boosts.",
        ]

    async def _generate_campaign_ideas_with_llm(
        self, context: Dict[str, Any], include_video: bool = False, system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        # Build the list of output keys based on video toggle
        output_keys = (
            "campaign_strategy, blog_ideas (5), tweet_ideas (8), reel_ideas (5), poster_ideas (5)"
        )
        if include_video:
            output_keys += ", short_video_ideas (5 — each a production script with: motion_prompt, voiceover_hook, visual_style)"

        # ── CRITICAL: Product-anchored prompt ─────────────────────────────────
        # The product name and description MUST be front-and-center so the LLM
        # anchors on the actual product, not just the category.
        product_name = context.get("product_name", "the product")
        product_desc = context.get("product_description", "")
        category = context.get("category", "")
        target_audience = context.get("target_audience", "")

        # Build visual identity section from DNA extraction
        visual_section = ""
        visual_identity = context.get("product_visual_identity")
        if visual_identity:
            vi_parts = []
            if visual_identity.get("color_palette"):
                vi_parts.append(f"Colors: {', '.join(visual_identity['color_palette'][:5])}")
            if visual_identity.get("primary_material"):
                vi_parts.append(f"Material: {visual_identity['primary_material']}")
            if visual_identity.get("surface_finish"):
                vi_parts.append(f"Finish: {visual_identity['surface_finish']}")
            if visual_identity.get("distinctive_features"):
                vi_parts.append(f"Distinctive features: {', '.join(visual_identity['distinctive_features'][:4])}")
            if visual_identity.get("brand_elements"):
                vi_parts.append(f"Brand elements: {', '.join(visual_identity['brand_elements'][:3])}")
            if vi_parts:
                visual_section = f"\nPRODUCT VISUAL IDENTITY (from image analysis):\n" + "\n".join(f"  • {p}" for p in vi_parts)
                visual_section += "\nIMPORTANT: Reference these visual details in poster_ideas and video scripts.\n"

        # Build competitor section from gap analysis
        competitor_section = ""
        comp_analysis = context.get("competitor_analysis")
        if comp_analysis:
            gaps = comp_analysis.get("gaps_to_exploit", [])
            unanswered = comp_analysis.get("audience_questions_unanswered", [])
            if gaps or unanswered:
                competitor_section = "\nCOMPETITOR GAPS TO EXPLOIT:\n"
                for g in gaps[:4]:
                    competitor_section += f"  • {g}\n"
                if unanswered:
                    competitor_section += "AUDIENCE QUESTIONS COMPETITORS MISS:\n"
                    for q in unanswered[:4]:
                        competitor_section += f"  • {q}\n"
                competitor_section += "Use these gaps and questions to shape blog/tweet/reel ideas.\n"

        prompt = (
            f"PRODUCT: {product_name}\n"
            f"DESCRIPTION: {product_desc}\n"
            f"CATEGORY: {category}\n"
            f"TARGET AUDIENCE: {target_audience}\n"
            f"{visual_section}"
            f"{competitor_section}\n"
            f"You are an elite performance marketing strategist. "
            f"Generate a COMPLETE marketing campaign specifically for '{product_name}'. "
            f"Every single idea (blog, tweet, reel, poster, video script) MUST be about '{product_name}' — "
            f"NOT generic category ideas about '{category}'. "
            f"Use the product name explicitly in every idea.\n\n"
            f"Return JSON with keys: {output_keys}.\n\n"
            f"Additional context (trend signals):\n{json.dumps(context, ensure_ascii=False)}"
        )

        url = f"{self.azure_endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
        system_instruction = system_prompt or "You are an elite performance marketing strategist. Return valid JSON only."
        if system_prompt and "Return valid JSON only." not in system_instruction:
            system_instruction += " MUST RETURN VALID JSON ONLY."

        payload = {
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1800,
            "temperature": 0.6,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

        logger.info(f"[CAMPAIGN LLM] Generating ideas for '{product_name}' in '{category}' (video={include_video})")

        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                result = json.loads(content)
                logger.info(f"[CAMPAIGN LLM] SUCCESS — got keys: {list(result.keys())}")
                return result
            except httpx.HTTPStatusError as e:
                logger.error(f"[CAMPAIGN LLM] HTTP {e.response.status_code}: {e.response.text[:500]}")
                return {}
            except json.JSONDecodeError as e:
                logger.error(f"[CAMPAIGN LLM] JSON parse failed: {e}. Raw content: {content[:500] if 'content' in dir() else 'N/A'}")
                return {}
            except Exception as e:
                logger.error(f"[CAMPAIGN LLM] Unexpected failure: {type(e).__name__}: {e}")
                return {}

    def _fallback_blog_ideas(self, request: ProductCampaignBriefRequest) -> List[str]:
        return [
            f"Ultimate guide to choosing the right {request.category} solution in 2026",
            f"{request.product_name} vs alternatives: transparent comparison",
            f"Top mistakes {request.target_audience} make in {request.category}",
            f"Case-study: improving results using {request.product_name}",
            f"ROI checklist before buying any {request.category} product",
        ]

    def _fallback_tweet_ideas(self, request: ProductCampaignBriefRequest) -> List[str]:
        return [
            f"Most {request.category} advice is outdated. Here is what works now 👇",
            f"3 lessons we learned building {request.product_name} for {request.target_audience}",
            f"Before buying a {request.category} product, ask these 5 questions.",
            f"The hidden cost nobody talks about in {request.category}",
            "Quick win: improve your outcomes with this 15-min framework.",
            f"Myth vs Reality in {request.category} (thread)",
            "If you only do one thing this week, do this.",
            f"Bookmark this: {request.category} decision checklist.",
        ]

    def _fallback_reel_ideas(self, request: ProductCampaignBriefRequest) -> List[str]:
        return [
            f"POV: You discovered {request.product_name} and everything changed",
            f"3-second hook showing {request.product_name} in action",
            f"Before/After transformation reel using {request.product_name} for {request.target_audience}",
            f"Top 3 reasons {request.target_audience} are switching to {request.product_name}",
            f"Unboxing + first impression of {request.product_name}",
        ]

    def _fallback_short_ideas(self, request: ProductCampaignBriefRequest) -> List[str]:
        return [
            f"YouTube Short: 5 myths about {request.product_name}",
            f"YouTube Short: Quick demo of {request.product_name} in 30 seconds",
            f"YouTube Short: {request.product_name} — is it worth the hype?",
            f"YouTube Short: How {request.target_audience} use {request.product_name}",
            f"YouTube Short: {request.product_name} vs the competition in 15 seconds",
        ]

    def _fallback_poster_ideas(self, request: ProductCampaignBriefRequest) -> List[str]:
        return [
            f"Bold hero poster featuring {request.product_name} with a single powerful tagline",
            f"Comparison poster: old way vs {request.product_name} way",
            f"Lifestyle poster showing {request.target_audience} using {request.product_name}",
            f"Minimalist social proof poster for {request.product_name} with key stat",
            f"Limited-time offer poster for {request.product_name}",
        ]

    def _normalize_campaign_strategy(self, value: Any, default: str) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()

        if isinstance(value, dict) and value:
            parts: List[str] = []
            for k, v in value.items():
                if v is None:
                    continue
                text = str(v).strip()
                if text:
                    parts.append(f"{k.replace('_', ' ').title()}: {text}")
            if parts:
                return " | ".join(parts)

        if isinstance(value, list):
            flat = [str(x).strip() for x in value if str(x).strip()]
            if flat:
                return " | ".join(flat)

        return default

    def _normalize_ideas(self, value: Any, fallback: List[str]) -> List[str]:
        if isinstance(value, list):
            cleaned = [str(v).strip() for v in value if isinstance(v, (str, int, float)) and str(v).strip()]
            if cleaned:
                return cleaned[: max(1, len(fallback))]

        if isinstance(value, str) and value.strip():
            split_lines = [line.strip(" -•\t") for line in value.splitlines() if line.strip()]
            if split_lines:
                return split_lines[: max(1, len(fallback))]

        return fallback

    async def _call_llm_analysis(self, competitor_data: str) -> Dict[str, Any]:
        """Calls Azure OpenAI to analyze the text data."""
        
        prompt = self.ANALYSIS_PROMPT.format(competitor_data=competitor_data)
        
        url = f"{self.azure_endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
        
        payload = {
            "messages": [
                {"role": "system", "content": "You are a helpful JSON-speaking Market Analyst assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.5,
            "response_format": { "type": "json_object" } # Force JSON mode if available
        }
        
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
            except Exception as e:
                logger.error(f"LLM Analysis failed: {e}")
                return {}

# Factory
def get_market_intel_service() -> MarketIntelService:
    return MarketIntelService()
