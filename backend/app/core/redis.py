"""
Redis Connection Pool
=====================

Provides a shared async Redis client for the job queue (ARQ),
pub/sub (WebSocket fan-out), and short-lived caching.
"""

import asyncio
import logging
from typing import Optional
from urllib.parse import urlparse

import redis.asyncio as aioredis
from arq.connections import RedisSettings

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# ── Singleton pool ──────────────────────────────────────────────────────────
_redis_pool: Optional[aioredis.Redis] = None


def _parse_redis_url(url: str) -> dict:
    """Parse a redis:// or rediss:// URL into connection kwargs."""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 6379,
        "password": parsed.password or None,
        "username": parsed.username or "default",
        "ssl": parsed.scheme == "rediss",
    }


async def get_redis() -> aioredis.Redis:
    """Return (and lazily create) the global async Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        params = _parse_redis_url(settings.REDIS_URL)
        _redis_pool = aioredis.Redis(
            host=params["host"],
            port=params["port"],
            password=params["password"],
            username=params["username"],
            ssl=params["ssl"],
            decode_responses=True,
            socket_connect_timeout=10,
            retry_on_timeout=True,
        )
        # Quick health check
        try:
            await _redis_pool.ping()
            logger.info(f"✅ Redis connected: {params['host']}:{params['port']} (ssl={params['ssl']})")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            _redis_pool = None
            raise
    return _redis_pool


async def close_redis():
    """Gracefully shut down the Redis pool."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
        logger.info("Redis connection closed")


def get_arq_redis_settings() -> RedisSettings:
    """
    Return ARQ-compatible RedisSettings from our REDIS_URL.
    
    ARQ workers use this to connect to the same Redis instance.
    """
    params = _parse_redis_url(settings.REDIS_URL)
    return RedisSettings(
        host=params["host"],
        port=params["port"],
        password=params["password"],
        ssl=params["ssl"],
        conn_timeout=15,
        conn_retries=5,
        conn_retry_delay=1.0,
    )


# ── Pub/Sub helpers for distributed WebSocket fan-out ───────────────────────

CHANNEL_PREFIX = "catalyst:job:"


async def publish_job_update(job_id: str, payload: dict):
    """
    Publish a job progress/complete message so ALL API nodes can push
    the update to any connected WebSocket clients.
    """
    import json
    r = await get_redis()
    channel = f"{CHANNEL_PREFIX}{job_id}"
    await r.publish(channel, json.dumps(payload))


async def enqueue_media_render(
    job_id: str,
    request_dict: dict,
    campaign_dict: dict,
    visual_dna_dict: Optional[dict],
    image_source: Optional[str],
    campaign_db_id: Optional[str],
):
    """
    Push a media-render job onto the ARQ task queue.

    The worker process picks it up independently of the API process.
    """
    from arq.connections import create_pool

    pool = await create_pool(get_arq_redis_settings())
    await pool.enqueue_job(
        "run_media_render",  # must match function name registered in WorkerSettings
        job_id=job_id,
        request_dict=request_dict,
        campaign_dict=campaign_dict,
        visual_dna_dict=visual_dna_dict,
        image_source=image_source,
        campaign_db_id=campaign_db_id,
    )
    await pool.aclose()
    logger.info(f"📤 Enqueued media_render job {job_id} to ARQ")


async def enqueue_rag_ingestion(campaign_id: str):
    """
    Push a RAG auto-ingestion job onto the ARQ task queue.
    """
    from arq.connections import create_pool

    pool = await create_pool(get_arq_redis_settings())
    await pool.enqueue_job("run_rag_ingestion", campaign_id=campaign_id)
    await pool.aclose()
    logger.info(f"📤 Enqueued RAG ingestion job for campaign {campaign_id}")
