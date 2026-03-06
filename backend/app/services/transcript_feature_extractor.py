"""
TRANSCRIPT FEATURE EXTRACTOR
=============================

Converts raw YouTube video transcripts into a fixed-dimension numeric
feature vector that the GNN can consume as a "content signal".

Feature Vector (8-dim):
  [0] hook_strength      – How attention-grabbing is the first 15 seconds?
  [1] cta_density         – How often does the creator push actions? (subscribe, buy, link…)
  [2] sentiment_score     – Net emotional tone (-1 negative … +1 positive), rescaled to 0-1
  [3] question_density    – Ratio of question-sentences (audience engagement proxy)
  [4] urgency_score       – Presence of urgency keywords (limited, now, hurry, today…)
  [5] phrase_diversity    – Unique bigrams / total bigrams (vocabulary richness)
  [6] avg_segment_length  – Mean word-count per transcript segment (pacing proxy)
  [7] keyword_density     – Ratio of strong subject-keywords vs filler (content depth)

Usage:
    extractor = TranscriptFeatureExtractor()
    # From a real YouTube video:
    features = await extractor.extract_from_video("dQw4w9WgXcQ")
    # -> [0.82, 0.15, 0.65, 0.08, 0.30, 0.45, 12.3, 0.22]

    # Generate synthetic features for training data bootstrapping:
    features = TranscriptFeatureExtractor.generate_synthetic(category="Tech")
"""

import re
import math
import random
import asyncio
import logging
from typing import List, Dict, Any, Optional
from collections import Counter

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# LEXICONS (lightweight, no external NLP dependency)
# ═══════════════════════════════════════════════════════════════════════════════

POSITIVE_WORDS = frozenset([
    "amazing", "awesome", "best", "brilliant", "excellent", "fantastic",
    "great", "incredible", "love", "outstanding", "perfect", "superb",
    "wonderful", "beautiful", "impressive", "powerful", "recommend",
    "favorite", "insane", "fire", "lit", "dope", "legit", "solid",
    "premium", "top", "epic", "killer", "goat", "blessed", "worth",
])

NEGATIVE_WORDS = frozenset([
    "bad", "worst", "terrible", "horrible", "awful", "hate", "ugly",
    "disappointing", "waste", "useless", "garbage", "cheap", "broken",
    "scam", "fake", "overpriced", "trash", "boring", "annoying", "avoid",
    "problem", "issue", "fail", "complaint", "flimsy", "pathetic",
])

CTA_KEYWORDS = frozenset([
    "subscribe", "like", "comment", "share", "follow", "click", "link",
    "buy", "shop", "order", "download", "sign", "join", "register",
    "check", "visit", "grab", "get", "use", "code", "discount",
    "offer", "deal", "free", "giveaway", "bell", "notification",
])

URGENCY_KEYWORDS = frozenset([
    "now", "today", "hurry", "limited", "last", "ending", "expire",
    "rush", "fast", "quick", "immediately", "soon", "deadline", "only",
    "flash", "exclusive", "running", "sold", "gone", "before",
    "midnight", "hours", "minutes", "don't miss", "act",
])

HOOK_POWER_WORDS = frozenset([
    "secret", "truth", "never", "stop", "why", "how", "shocking",
    "exposed", "revealed", "mistake", "wrong", "warning", "hack",
    "trick", "myth", "actually", "real", "hidden", "nobody",
    "everyone", "finally", "illegal", "banned", "crazy", "insane",
])

STOP_WORDS = frozenset([
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "is", "it", "be", "as", "do", "so",
    "if", "not", "no", "can", "will", "just", "i", "me", "my",
    "you", "your", "we", "our", "he", "she", "they", "them", "its",
    "was", "were", "been", "has", "had", "are", "am", "have", "this",
    "that", "these", "those", "what", "which", "who", "whom",
    "than", "then", "very", "too", "also", "um", "uh", "like",
])

# Content-depth keywords per category (for keyword_density scoring)
CATEGORY_SUBJECT_KEYWORDS = {
    "Tech": frozenset([
        "processor", "battery", "display", "camera", "performance", "speed",
        "specs", "benchmark", "review", "comparison", "unbox", "setup",
        "android", "ios", "wireless", "bluetooth", "chip", "ram", "storage",
        "software", "hardware", "update", "features", "design", "build",
        "quality", "test", "gaming", "fps", "resolution", "screen",
    ]),
    "Fashion": frozenset([
        "outfit", "style", "trend", "collection", "brand", "fabric",
        "color", "pattern", "accessory", "wardrobe", "look", "season",
        "summer", "winter", "casual", "formal", "designer", "boutique",
        "aesthetic", "luxury", "streetwear", "vintage", "sustainable",
        "haul", "try", "wear", "size", "fit", "runway", "couture",
    ]),
    "Finance": frozenset([
        "invest", "stock", "market", "portfolio", "dividend", "return",
        "risk", "mutual", "fund", "sip", "index", "trading", "crypto",
        "bitcoin", "nifty", "sensex", "ipo", "profit", "loss", "tax",
        "saving", "compound", "interest", "inflation", "budget", "wealth",
        "passive", "income", "asset", "debt", "equity", "bull", "bear",
    ]),
    "General": frozenset([
        "trending", "viral", "popular", "content", "creator", "audience",
        "engagement", "reach", "growth", "followers", "views", "algorithm",
    ]),
}


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE VECTOR DIMENSION
# ═══════════════════════════════════════════════════════════════════════════════

CONTENT_FEATURE_DIM = 8

FEATURE_NAMES = [
    "hook_strength",
    "cta_density",
    "sentiment_score",
    "question_density",
    "urgency_score",
    "phrase_diversity",
    "avg_segment_length",
    "keyword_density",
]


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class TranscriptFeatureExtractor:
    """
    Extracts an 8-dim numeric content feature vector from a YouTube transcript.

    Can also generate plausible synthetic feature vectors for training data
    bootstrapping (so the GNN can start learning before real transcripts are
    available for every campaign).
    """

    def __init__(self):
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            self.transcript_client = YouTubeTranscriptApi()
        except Exception:
            self.transcript_client = None
            logger.warning("youtube-transcript-api not available; real extraction disabled.")

    # ─── PUBLIC: extract from a real video ────────────────────────────────

    async def extract_from_video(
        self,
        video_id: str,
        category: str = "General",
    ) -> List[float]:
        """
        Fetch transcript for *video_id* and return 8-dim feature vector.

        Falls back to synthetic generation if transcript unavailable.
        """
        raw_segments = await self._fetch_transcript(video_id)

        if not raw_segments:
            logger.info(f"No transcript for {video_id}; generating synthetic features.")
            return self.generate_synthetic(category)

        return self._compute_features(raw_segments, category)

    # ─── PUBLIC: batch extraction ─────────────────────────────────────────

    async def extract_batch(
        self,
        video_ids: List[str],
        category: str = "General",
    ) -> List[List[float]]:
        """Extract features for a list of videos, averaging into one vector."""
        tasks = [self.extract_from_video(vid, category) for vid in video_ids]
        all_features = await asyncio.gather(*tasks)
        return list(all_features)

    async def extract_averaged(
        self,
        video_ids: List[str],
        category: str = "General",
    ) -> List[float]:
        """Extract features for multiple videos and return the mean vector."""
        all_features = await self.extract_batch(video_ids, category)
        if not all_features:
            return self.generate_synthetic(category)

        n = len(all_features)
        dim = CONTENT_FEATURE_DIM
        averaged = [
            sum(f[i] for f in all_features) / n
            for i in range(dim)
        ]
        return [round(v, 4) for v in averaged]

    # ─── PUBLIC: synthetic generation ─────────────────────────────────────

    @staticmethod
    def generate_synthetic(category: str = "General") -> List[float]:
        """
        Generate a plausible 8-dim feature vector for a given category.

        Category-specific priors make the synthetic data realistic:
        - Tech: higher keyword density, moderate hooks
        - Fashion: higher sentiment, strong hooks
        - Finance: higher urgency, more CTAs
        - General: balanced baseline
        """

        # Base distributions per category (mean, std) for each feature
        profiles = {
            "Tech": {
                "hook_strength":      (0.55, 0.18),
                "cta_density":        (0.20, 0.10),
                "sentiment_score":    (0.58, 0.12),
                "question_density":   (0.12, 0.06),
                "urgency_score":      (0.20, 0.12),
                "phrase_diversity":   (0.40, 0.12),
                "avg_segment_length": (0.50, 0.15),  # normalized 0-1
                "keyword_density":    (0.35, 0.10),
            },
            "Fashion": {
                "hook_strength":      (0.70, 0.15),
                "cta_density":        (0.30, 0.12),
                "sentiment_score":    (0.72, 0.10),
                "question_density":   (0.08, 0.05),
                "urgency_score":      (0.35, 0.15),
                "phrase_diversity":   (0.35, 0.10),
                "avg_segment_length": (0.45, 0.12),
                "keyword_density":    (0.25, 0.08),
            },
            "Finance": {
                "hook_strength":      (0.60, 0.15),
                "cta_density":        (0.25, 0.10),
                "sentiment_score":    (0.50, 0.08),
                "question_density":   (0.18, 0.08),
                "urgency_score":      (0.40, 0.15),
                "phrase_diversity":   (0.50, 0.12),
                "avg_segment_length": (0.55, 0.15),
                "keyword_density":    (0.40, 0.10),
            },
            "General": {
                "hook_strength":      (0.50, 0.20),
                "cta_density":        (0.18, 0.12),
                "sentiment_score":    (0.55, 0.15),
                "question_density":   (0.10, 0.06),
                "urgency_score":      (0.22, 0.15),
                "phrase_diversity":   (0.38, 0.15),
                "avg_segment_length": (0.48, 0.15),
                "keyword_density":    (0.20, 0.10),
            },
        }

        profile = profiles.get(category, profiles["General"])
        vector = []

        for feat_name in FEATURE_NAMES:
            mean, std = profile[feat_name]
            val = random.gauss(mean, std)
            val = max(0.0, min(1.0, val))  # clamp to [0, 1]
            vector.append(round(val, 4))

        return vector

    # ─── INTERNAL: transcript fetching ────────────────────────────────────

    async def _fetch_transcript(self, video_id: str) -> List[Dict[str, Any]]:
        """Fetch raw transcript segments from YouTube."""
        if not self.transcript_client:
            return []

        def _fetch():
            try:
                fetched = self.transcript_client.fetch(
                    video_id, languages=["en", "en-IN", "hi"]
                )
                return fetched.to_raw_data() if fetched else []
            except Exception as e:
                logger.debug(f"Transcript fetch failed for {video_id}: {e}")
                return []

        return await asyncio.to_thread(_fetch)

    # ─── INTERNAL: feature computation ────────────────────────────────────

    def _compute_features(
        self,
        segments: List[Dict[str, Any]],
        category: str,
    ) -> List[float]:
        """
        Core feature extraction from raw transcript segments.

        Each segment is: {"text": "...", "start": float, "duration": float}
        """
        texts = [str(s.get("text", "")).strip() for s in segments if s.get("text")]
        if not texts:
            return self.generate_synthetic(category)

        full_text = " ".join(texts)
        all_words = re.findall(r"[A-Za-z][A-Za-z0-9']{1,}", full_text.lower())
        total_words = len(all_words) or 1

        # ── Feature 0: Hook Strength ──────────────────────────────────────
        # How powerful are the first ~15 seconds (first 5 segments)?
        hook_text = " ".join(texts[:5]).lower()
        hook_words = re.findall(r"[a-z]{2,}", hook_text)
        hook_power_count = sum(1 for w in hook_words if w in HOOK_POWER_WORDS)
        has_question = 1.0 if "?" in hook_text else 0.0
        hook_strength = min(1.0, (hook_power_count / max(len(hook_words), 1)) * 5 + has_question * 0.2)

        # ── Feature 1: CTA Density ────────────────────────────────────────
        cta_count = sum(1 for w in all_words if w in CTA_KEYWORDS)
        cta_density = min(1.0, cta_count / (total_words / 50))  # per 50 words

        # ── Feature 2: Sentiment Score ────────────────────────────────────
        pos_count = sum(1 for w in all_words if w in POSITIVE_WORDS)
        neg_count = sum(1 for w in all_words if w in NEGATIVE_WORDS)
        raw_sentiment = (pos_count - neg_count) / max(pos_count + neg_count, 1)
        sentiment_score = (raw_sentiment + 1.0) / 2.0  # rescale [-1,1] -> [0,1]

        # ── Feature 3: Question Density ───────────────────────────────────
        question_segments = sum(1 for t in texts if "?" in t)
        question_density = min(1.0, question_segments / max(len(texts), 1))

        # ── Feature 4: Urgency Score ──────────────────────────────────────
        urgency_count = sum(1 for w in all_words if w in URGENCY_KEYWORDS)
        urgency_score = min(1.0, urgency_count / (total_words / 80))  # per 80 words

        # ── Feature 5: Phrase Diversity ───────────────────────────────────
        content_words = [w for w in all_words if w not in STOP_WORDS and len(w) > 2]
        if len(content_words) >= 2:
            bigrams = [
                f"{content_words[i]} {content_words[i+1]}"
                for i in range(len(content_words) - 1)
            ]
            unique_bigrams = len(set(bigrams))
            phrase_diversity = min(1.0, unique_bigrams / max(len(bigrams), 1))
        else:
            phrase_diversity = 0.0

        # ── Feature 6: Avg Segment Length (normalized) ────────────────────
        seg_lengths = [len(t.split()) for t in texts]
        raw_avg = sum(seg_lengths) / max(len(seg_lengths), 1)
        # Normalize: typical segment is 5-25 words, map to 0-1
        avg_segment_length = min(1.0, raw_avg / 25.0)

        # ── Feature 7: Keyword Density ────────────────────────────────────
        subject_keywords = CATEGORY_SUBJECT_KEYWORDS.get(category, CATEGORY_SUBJECT_KEYWORDS["General"])
        kw_count = sum(1 for w in all_words if w in subject_keywords)
        keyword_density = min(1.0, kw_count / (total_words / 30))  # per 30 words

        return [
            round(hook_strength, 4),
            round(cta_density, 4),
            round(sentiment_score, 4),
            round(question_density, 4),
            round(urgency_score, 4),
            round(phrase_diversity, 4),
            round(avg_segment_length, 4),
            round(keyword_density, 4),
        ]

    # ─── UTILITY: feature dict ────────────────────────────────────────────

    @staticmethod
    def vector_to_dict(vector: List[float]) -> Dict[str, float]:
        """Convert a feature vector to a named dictionary."""
        return {
            name: vector[i] if i < len(vector) else 0.0
            for i, name in enumerate(FEATURE_NAMES)
        }

    @staticmethod
    def dict_to_vector(feature_dict: Dict[str, float]) -> List[float]:
        """Convert a named feature dictionary back to a list."""
        return [feature_dict.get(name, 0.0) for name in FEATURE_NAMES]
