
import logging
from typing import List, Dict, Optional, Any
from uuid import UUID

from sqlalchemy import func, text, desc
from sqlalchemy.orm import Session

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Flag to track if pgvector table is available
_pgvector_available: Optional[bool] = None


class RagService:
    """
    Retrieval-Augmented Generation Service
    
    Two modes:
    1. Full RAG (pgvector): Semantic search via embeddings when knowledge_chunks table exists
    2. Fallback (direct SQL): Queries generated_campaigns table directly when pgvector is unavailable
    
    This ensures the chatbot ALWAYS returns real user data, never hallucinations.
    """

    def __init__(self, db: Session):
        self.db = db
        self._embedding_client = None

    def _get_embedding_client(self):
        """Lazy-init the embedding client — uses Azure OpenAI."""
        if self._embedding_client is None:
            from openai import AsyncAzureOpenAI
            self._embedding_client = AsyncAzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version="2024-02-15-preview",
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
        return self._embedding_client

    @property
    def embedding_model(self) -> str:
        return settings.AZURE_EMBEDDING_DEPLOYMENT

    def _check_pgvector_available(self) -> bool:
        """Check if the knowledge_chunks table exists in the database."""
        global _pgvector_available
        if _pgvector_available is not None:
            return _pgvector_available
        try:
            self.db.execute(text("SELECT 1 FROM knowledge_chunks LIMIT 0;"))
            _pgvector_available = True
            logger.info("✅ RAG: knowledge_chunks table found — full pgvector RAG enabled")
        except Exception:
            _pgvector_available = False
            self.db.rollback()  # Clear the failed transaction
            logger.warning("⚠️ RAG: knowledge_chunks table NOT found — using direct DB fallback")
        return _pgvector_available

    # ─── Embedding Generation ────────────────────────────────────────────────

    async def generate_embedding(self, text_chunk: str) -> List[float]:
        """Generate vector embedding for a text chunk."""
        try:
            client = self._get_embedding_client()
            response = await client.embeddings.create(
                input=text_chunk,
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise RuntimeError(f"Embedding API failed: {e}")

    # ─── Campaign Ingestion ──────────────────────────────────────────────────

    async def ingest_campaign(self, campaign) -> int:
        """
        Auto-ingest a generated campaign into Knowledge Chunks.
        Stores ALL generated content, not just strategy.
        Returns count of chunks ingested.
        """
        if not self._check_pgvector_available():
            logger.warning("Skipping RAG ingestion — knowledge_chunks table doesn't exist. Run supabase_rag_migration.sql first.")
            return 0

        from backend.app.db.models import KnowledgeChunk

        logger.info(f"Ingesting campaign {campaign.id} into RAG memory...")
        chunks = []

        # 1. Campaign Strategy (High Value)
        if campaign.campaign_strategy:
            chunks.append({
                "content": f"Campaign Strategy for {campaign.product_name} ({campaign.category}): {campaign.campaign_strategy}",
                "category": "campaign_strategy",
                "source_id": str(campaign.id),
                "confidence": 0.95
            })

        # 2. Product Context
        if campaign.product_description:
            chunks.append({
                "content": f"Product: {campaign.product_name}. Category: {campaign.category or 'N/A'}. Description: {campaign.product_description}. Target Audience: {campaign.target_audience or 'N/A'}. Region: {campaign.region_code or 'N/A'}.",
                "category": "product_context",
                "source_id": str(campaign.id),
                "confidence": 0.9
            })

        # 3. All Content Ideas (individually for better retrieval)
        idea_types = [
            ("blog_ideas", "blog_idea"),
            ("tweet_ideas", "tweet_idea"),
            ("reel_ideas", "reel_idea"),
            ("short_video_ideas", "video_idea"),
            ("poster_ideas", "poster_idea"),
        ]
        for field, category in idea_types:
            ideas = getattr(campaign, field, None) or []
            if ideas:
                # Batch all ideas of same type into one chunk to save embedding calls
                ideas_text = "\n".join(f"- {idea}" for idea in ideas[:10])  # Cap at 10
                chunks.append({
                    "content": f"{category.replace('_', ' ').title()}s for {campaign.product_name}:\n{ideas_text}",
                    "category": category,
                    "source_id": str(campaign.id),
                    "confidence": 0.85
                })

        # 4. Competitor Gap Analysis
        if campaign.gap_analysis:
            gap_text = str(campaign.gap_analysis)[:1000]  # Truncate to avoid huge embeddings
            chunks.append({
                "content": f"Competitor Analysis for {campaign.product_name}: {gap_text}",
                "category": "competitor_analysis",
                "source_id": str(campaign.id),
                "confidence": 0.85
            })

        # 5. Trend Keywords
        if campaign.trend_keywords:
            keywords = ", ".join(campaign.trend_keywords[:20])
            chunks.append({
                "content": f"Trending Keywords in {campaign.category} ({campaign.region_code}): {keywords}",
                "category": "market_trends",
                "source_id": str(campaign.id),
                "confidence": 0.8
            })

        # 6. Scoring
        if campaign.scoring:
            chunks.append({
                "content": f"Campaign Score for {campaign.product_name}: AI Score {campaign.scoring.get('ai_score', 'N/A')}, Verdict: {campaign.scoring.get('verdict', 'N/A')}",
                "category": "campaign_scoring",
                "source_id": str(campaign.id),
                "confidence": 0.8
            })

        # Process and save all chunks
        ingested = 0
        for item in chunks:
            try:
                embedding = await self.generate_embedding(item["content"])
                chunk = KnowledgeChunk(
                    user_id=campaign.user_id,
                    project_id=campaign.project_id,
                    content=item["content"],
                    embedding=embedding,
                    category=item["category"],
                    source_type="campaign_generation",
                    source_id=item["source_id"],
                    confidence_score=item["confidence"]
                )
                self.db.add(chunk)
                ingested += 1
            except Exception as e:
                logger.error(f"Failed to ingest chunk '{item['category']}': {e}")

        try:
            self.db.commit()
            logger.info(f"✅ Ingested {ingested}/{len(chunks)} knowledge chunks from campaign {campaign.id}")
        except Exception as e:
            logger.error(f"Failed to commit knowledge chunks: {e}")
            self.db.rollback()
            ingested = 0

        return ingested

    # ─── Chat Turn Storage ───────────────────────────────────────────────────

    async def store_chat_turn(self, user_id: UUID, user_message: str, bot_reply: str):
        """Store a chat exchange as a knowledge chunk for future retrieval."""
        if not self._check_pgvector_available():
            return

        from backend.app.db.models import KnowledgeChunk

        # Only store substantive exchanges (skip greetings, short messages)
        if len(user_message) < 20 and len(bot_reply) < 50:
            return

        content = f"User asked: {user_message[:500]}\nAssistant replied: {bot_reply[:500]}"
        try:
            embedding = await self.generate_embedding(content)
            chunk = KnowledgeChunk(
                user_id=user_id,
                content=content,
                embedding=embedding,
                category="chat_history",
                source_type="chat_turn",
                confidence_score=0.7
            )
            self.db.add(chunk)
            self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to store chat turn: {e}")
            self.db.rollback()

    # ─── Search ──────────────────────────────────────────────────────────────

    async def search(self, query: str, user_id: UUID, limit: int = 5) -> List[Any]:
        """
        Search for relevant knowledge.
        Uses pgvector if available, otherwise falls back to direct campaign DB query.
        
        Returns list of objects with .content and .category attributes.
        """
        if self._check_pgvector_available():
            return await self._search_pgvector(query, user_id, limit)
        else:
            return self._search_fallback(query, user_id, limit)

    async def _search_pgvector(self, query: str, user_id: UUID, limit: int) -> List[Any]:
        """Full semantic search via pgvector embeddings."""
        from backend.app.db.models import KnowledgeChunk

        query_vec = await self.generate_embedding(query)
        results = self.db.query(KnowledgeChunk).filter(
            KnowledgeChunk.user_id == user_id
        ).order_by(
            KnowledgeChunk.embedding.cosine_distance(query_vec)
        ).limit(limit).all()

        if results:
            logger.info(f"🔍 RAG pgvector search returned {len(results)} chunks for user {user_id}")
        return results

    def _search_fallback(self, query: str, user_id: UUID, limit: int) -> List[Any]:
        """
        Fallback: directly query GeneratedCampaign table.
        No semantic search, but at least returns REAL user data instead of hallucinations.
        """
        from backend.app.db.models import GeneratedCampaign

        # Get user's recent campaigns
        campaigns = self.db.query(GeneratedCampaign).filter(
            GeneratedCampaign.user_id == user_id
        ).order_by(
            desc(GeneratedCampaign.created_at)
        ).limit(limit).all()

        if not campaigns:
            return []

        # Convert to chunk-like objects so the chatbot can use them
        class FallbackChunk:
            def __init__(self, content: str, category: str):
                self.content = content
                self.category = category

        chunks = []
        for c in campaigns:
            # Build a rich text summary of each campaign
            parts = [f"Campaign for '{c.product_name}'"]
            if c.category:
                parts.append(f"Category: {c.category}")
            if c.target_audience:
                parts.append(f"Audience: {c.target_audience}")
            if c.campaign_strategy:
                parts.append(f"Strategy: {c.campaign_strategy[:300]}")
            if c.blog_ideas:
                parts.append(f"Blog Ideas: {', '.join(str(i) for i in c.blog_ideas[:3])}")
            if c.tweet_ideas:
                parts.append(f"Tweet Ideas: {', '.join(str(i) for i in c.tweet_ideas[:3])}")
            if c.reel_ideas:
                parts.append(f"Reel Ideas: {', '.join(str(i) for i in c.reel_ideas[:3])}")
            if c.poster_ideas:
                parts.append(f"Poster Ideas: {', '.join(str(i) for i in c.poster_ideas[:3])}")
            if c.scoring:
                parts.append(f"Score: {c.scoring.get('verdict', 'N/A')}")
            if c.created_at:
                parts.append(f"Created: {c.created_at.strftime('%Y-%m-%d')}")

            chunks.append(FallbackChunk(
                content=". ".join(parts),
                category="campaign_history"
            ))

        logger.info(f"🔍 RAG fallback returned {len(chunks)} campaigns for user {user_id}")
        return chunks


def get_rag_service(db: Session) -> RagService:
    return RagService(db)
