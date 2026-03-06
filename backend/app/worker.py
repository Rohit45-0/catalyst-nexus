"""
ARQ Worker — Media Render Queue
================================

Run with:
    python -m backend.app.worker

This is a SEPARATE process from FastAPI. It picks up media-render
jobs from Redis, generates posters + video, and publishes progress
updates back through Redis pub/sub so every API node can relay
them over WebSocket.
"""

import asyncio
import logging
import uuid as _uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

from arq.connections import RedisSettings
from arq.worker import Retry
import httpx
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

# ── Bootstrap logging before anything else ──────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("catalyst.worker")
T = TypeVar("T")

# ── Lazy imports so the worker boots fast ───────────────────────────────────
# We import heavy modules only inside the task functions.


def _get_redis_settings() -> RedisSettings:
    """Build ARQ RedisSettings from the shared config."""
    from backend.app.core.redis import get_arq_redis_settings
    return get_arq_redis_settings()


def _worker_settings():
    from backend.app.core.config import settings
    return settings


def _retry_delay_seconds() -> int:
    settings = _worker_settings()
    return max(1, int(settings.WORKER_TRANSIENT_RETRY_DELAY_SECONDS or 60))


def _looks_transient_text(text: str) -> bool:
    value = (text or "").lower()
    transient_markers = [
        "429",
        "rate limit",
        "too many requests",
        "timed out",
        "timeout",
        "temporarily unavailable",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "connection reset",
        "connection aborted",
        "connection refused",
        "network",
    ]
    return any(marker in value for marker in transient_markers)


def _openai_transient_exception_types() -> tuple:
    """Best-effort OpenAI transient exception discovery across SDK versions."""
    try:
        import openai  # type: ignore
    except Exception:
        return ()

    names = [
        "RateLimitError",
        "APIConnectionError",
        "APITimeoutError",
        "InternalServerError",
        "ServiceUnavailableError",
    ]
    resolved = []
    for name in names:
        exc_type = getattr(openai, name, None)
        if isinstance(exc_type, type):
            resolved.append(exc_type)
    return tuple(resolved)


def _is_transient_exception(exc: Exception) -> bool:
    if isinstance(exc, CircuitBreakerOpenError):
        return True

    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError, OSError)):
        return True

    if isinstance(exc, httpx.TimeoutException):
        return True

    if isinstance(exc, httpx.RequestError):
        return True

    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code if exc.response is not None else 0
        if status_code in {408, 409, 425, 429, 500, 502, 503, 504}:
            return True

    openai_types = _openai_transient_exception_types()
    if openai_types and isinstance(exc, openai_types):
        return True

    return _looks_transient_text(str(exc))


def _safe_error_summary(exc: Exception, max_len: int = 180) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return message[:max_len]


class CircuitBreakerOpenError(RuntimeError):
    """Raised when a circuit is open and calls should be deferred."""


@dataclass
class _CircuitState:
    state: str = "closed"  # closed | open | half_open
    consecutive_failures: int = 0
    opened_at: Optional[datetime] = None
    half_open_successes: int = 0


_CIRCUITS: Dict[str, _CircuitState] = {}
_CIRCUIT_LOCK = asyncio.Lock()


async def _circuit_before_call(circuit_name: str):
    settings = _worker_settings()
    recovery_seconds = max(1, int(settings.WORKER_CIRCUIT_BREAKER_RECOVERY_SECONDS or 60))

    async with _CIRCUIT_LOCK:
        state = _CIRCUITS.setdefault(circuit_name, _CircuitState())
        if state.state != "open":
            return

        elapsed = (datetime.utcnow() - state.opened_at).total_seconds() if state.opened_at else 0
        if elapsed >= recovery_seconds:
            state.state = "half_open"
            state.half_open_successes = 0
            logger.warning(f"[CIRCUIT] {circuit_name} moved to half-open")
            return

        remaining = max(1, int(recovery_seconds - elapsed))
        raise CircuitBreakerOpenError(
            f"Circuit '{circuit_name}' is open; retry after ~{remaining}s"
        )


async def _circuit_record_success(circuit_name: str):
    settings = _worker_settings()
    success_threshold = max(1, int(settings.WORKER_CIRCUIT_BREAKER_SUCCESS_THRESHOLD or 2))

    async with _CIRCUIT_LOCK:
        state = _CIRCUITS.setdefault(circuit_name, _CircuitState())
        if state.state == "half_open":
            state.half_open_successes += 1
            if state.half_open_successes >= success_threshold:
                state.state = "closed"
                state.consecutive_failures = 0
                state.opened_at = None
                state.half_open_successes = 0
                logger.info(f"[CIRCUIT] {circuit_name} closed after recovery")
            return

        state.consecutive_failures = 0


async def _circuit_record_failure(circuit_name: str, exc: Exception):
    settings = _worker_settings()
    failure_threshold = max(1, int(settings.WORKER_CIRCUIT_BREAKER_FAILURE_THRESHOLD or 3))

    async with _CIRCUIT_LOCK:
        state = _CIRCUITS.setdefault(circuit_name, _CircuitState())

        # Any failure while half-open re-opens the circuit immediately.
        if state.state == "half_open":
            state.state = "open"
            state.opened_at = datetime.utcnow()
            state.half_open_successes = 0
            state.consecutive_failures = failure_threshold
            logger.warning(
                f"[CIRCUIT] {circuit_name} re-opened from half-open: {_safe_error_summary(exc)}"
            )
            return

        state.consecutive_failures += 1
        if state.consecutive_failures >= failure_threshold:
            state.state = "open"
            state.opened_at = datetime.utcnow()
            state.half_open_successes = 0
            logger.warning(
                f"[CIRCUIT] {circuit_name} opened after {state.consecutive_failures} failures: {_safe_error_summary(exc)}"
            )


async def _defer_retry(job_id: Optional[str], reason: str):
    delay = _retry_delay_seconds()
    if job_id:
        try:
            from backend.app.db.schemas import JobStatus
            await _update_job(
                job_id,
                status=JobStatus.QUEUED.value,
                message=f"Transient upstream issue. Retrying in {delay}s. ({reason})",
            )
        except Exception as status_err:
            logger.warning(f"[WORKER] Failed to mark job {job_id} as queued before retry: {status_err}")
    raise Retry(defer=delay)


async def _run_with_tenacity(operation_name: str, coro_factory: Callable[[], Awaitable[T]]) -> T:
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(_is_transient_exception),
        reraise=True,
    ):
        with attempt:
            return await coro_factory()
    raise RuntimeError(f"{operation_name} failed unexpectedly without a tenacity result")


async def _execute_with_resilience(
    *,
    job_id: Optional[str],
    circuit_name: str,
    operation_name: str,
    coro_factory: Callable[[], Awaitable[T]],
) -> T:
    try:
        await _circuit_before_call(circuit_name)
        result = await _run_with_tenacity(operation_name, coro_factory)
    except Exception as exc:
        if not isinstance(exc, CircuitBreakerOpenError):
            await _circuit_record_failure(circuit_name, exc)
        if _is_transient_exception(exc):
            await _defer_retry(job_id, f"{operation_name}: {_safe_error_summary(exc)}")
        raise

    await _circuit_record_success(circuit_name)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Update job in Postgres + publish to Redis pub/sub
# ─────────────────────────────────────────────────────────────────────────────

async def _update_job(
    job_id: str,
    *,
    status: str = None,
    message: str = None,
    progress: int = None,
    result: dict = None,
    error: str = None,
):
    """
    Persist job status to Postgres AND broadcast via Redis pub/sub
    so the API nodes can relay updates over WebSocket.
    """
    from backend.app.db.base import SessionLocal
    from backend.app.db.models import Job
    from backend.app.db.schemas import JobStatus
    from backend.app.core.redis import publish_job_update

    db = SessionLocal()
    try:
        job = db.get(Job, _uuid.UUID(job_id))
        if not job:
            logger.warning(f"Job {job_id} not found in DB")
            return

        if status:
            job.status = status
        if message:
            job.status_message = message
        if progress is not None:
            job.progress = max(0, min(100, progress))
        if result is not None:
            job.result = result
            job.output_payload = result
        if error:
            job.error = error
        if status in (JobStatus.COMPLETED.value, JobStatus.FAILED.value):
            job.completed_at = datetime.utcnow()
        if status == JobStatus.RUNNING.value and not job.started_at:
            job.started_at = datetime.utcnow()

        db.commit()

        # Broadcast via Redis pub/sub → all API nodes
        await publish_job_update(job_id, {
            "job_id": job_id,
            "status": job.status,
            "message": job.status_message,
            "progress": job.progress,
            "error": job.error,
            "result": job.result,
        })

    except Exception as e:
        db.rollback()
        logger.error(f"[WORKER] Failed to update job {job_id}: {e}")
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# TASK: Media Render (posters + video)
# ─────────────────────────────────────────────────────────────────────────────

async def run_media_render(
    ctx: dict,
    *,
    job_id: str,
    request_dict: dict,
    campaign_dict: dict,
    visual_dna_dict: Optional[Dict[str, Any]],
    image_source: Optional[str],
    campaign_db_id: Optional[str],
):
    """
    ARQ task: generate poster images + video for a campaign.

    This runs in the worker process, completely decoupled from FastAPI.
    """
    logger.info(f"[WORKER] 🎬 Starting media render: {job_id}")

    # Late imports to avoid loading the entire app on worker boot
    from backend.app.db.schemas import (
        FullCampaignPipelineRequest,
        CampaignGenerationResponse,
        AssetDownloadLink,
        JobStatus,
    )
    from backend.app.db.base import SessionLocal
    from backend.app.db.models import GeneratedCampaign

    # Reconstruct Pydantic models from serialized dicts
    request = FullCampaignPipelineRequest(**request_dict)
    campaign = CampaignGenerationResponse(**campaign_dict)

    circuit_name = "media_render"

    await _update_job(
        job_id,
        status=JobStatus.RUNNING.value,
        message="Generating poster assets...",
        progress=5,
    )

    poster_assets: List[AssetDownloadLink] = []
    video_asset: Optional[AssetDownloadLink] = None

    # ── Step 1: Posters ──────────────────────────────────────────────────
    try:
        from backend.app.api.v1.market_intel import _generate_poster_assets

        async def _render_posters():
            return await _generate_poster_assets(
                request, campaign, visual_dna_dict, image_source
            )

        poster_assets = await _execute_with_resilience(
            job_id=job_id,
            circuit_name=circuit_name,
            operation_name="poster_generation",
            coro_factory=_render_posters,
        )
        poster_progress = 50 if request.video_generation_enabled else 90
        await _update_job(
            job_id,
            message=f"Posters complete ({len(poster_assets)} generated). "
                    f"{'Rendering video...' if request.video_generation_enabled else 'Finalizing...'}",
            progress=poster_progress,
        )
    except Retry:
        raise
    except Exception as e:
        logger.error(f"[WORKER] Poster generation failed: {e}")
        await _update_job(
            job_id,
            message=f"Poster generation failed: {e}; continuing to video...",
            progress=50,
        )

    # ── Step 2: Video ────────────────────────────────────────────────────
    if request.video_generation_enabled:
        try:
            from backend.app.api.v1.market_intel import _generate_video_asset

            async def _render_video():
                return await _generate_video_asset(request, campaign, image_source)

            video_asset = await _execute_with_resilience(
                job_id=job_id,
                circuit_name=circuit_name,
                operation_name="video_generation",
                coro_factory=_render_video,
            )
            await _update_job(
                job_id,
                message="Video generation complete. Finalizing...",
                progress=90,
            )
        except Retry:
            raise
        except Exception as e:
            logger.error(f"[WORKER] Video generation failed: {e}")
            await _update_job(
                job_id,
                message=f"Video generation failed: {e}; finalizing...",
                progress=90,
            )

    # ── Step 3: Finalize ─────────────────────────────────────────────────
    result_payload = {
        "poster_assets": [a.model_dump(mode="json") for a in poster_assets],
        "video_asset": video_asset.model_dump(mode="json") if video_asset else None,
        "downloads": {},
    }
    for idx, asset in enumerate(poster_assets):
        result_payload["downloads"][f"poster_{idx + 1}"] = asset.download_url
    if video_asset:
        result_payload["downloads"]["video_asset"] = video_asset.download_url

    await _update_job(
        job_id,
        status=JobStatus.COMPLETED.value,
        message="All media assets generated successfully!",
        progress=100,
        result=result_payload,
    )

    # ── Update GeneratedCampaign row with poster assets ──────────────────
    if campaign_db_id:
        db = SessionLocal()
        try:
            gc = db.get(GeneratedCampaign, _uuid.UUID(campaign_db_id))
            if gc:
                gc.poster_assets = [
                    {"name": a.name, "download_url": a.download_url, "asset_type": a.asset_type}
                    for a in poster_assets
                ]
                db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"[WORKER] Failed to update GeneratedCampaign: {e}")
        finally:
            db.close()

    logger.info(f"[WORKER] ✅ Media render complete: {job_id}")


# ─────────────────────────────────────────────────────────────────────────────
# TASK: Generic job processing (identity extraction, etc.)
# ─────────────────────────────────────────────────────────────────────────────

async def run_generic_job(
    ctx: dict,
    *,
    job_id: str,
    job_type: str,
    parameters: dict,
):
    """
    ARQ task: process a generic job (identity extraction, motion transfer, etc.)
    Falls back to the existing TaskEngine for non-media jobs.
    """
    logger.info(f"[WORKER] Processing generic job {job_id} (type={job_type})")

    from backend.app.core.engine import TaskEngine
    engine = TaskEngine()

    async def _run_engine_job():
        result = await engine.process_job(job_id=job_id, job_type=job_type, parameters=parameters)

        # TaskEngine may swallow transient upstream exceptions and return
        # a failed payload instead of raising. Re-surface transient failures
        # so ARQ can defer/retry safely.
        if isinstance(result, dict) and str(result.get("status") or "").lower() == "failed":
            err = str(result.get("error") or result.get("message") or "")
            if _looks_transient_text(err):
                raise RuntimeError(err or "Transient upstream failure")

        return result

    await _execute_with_resilience(
        job_id=job_id,
        circuit_name="generic_job",
        operation_name=f"generic_job:{job_type}",
        coro_factory=_run_engine_job,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TASK: RAG Ingestion
# ─────────────────────────────────────────────────────────────────────────────

async def run_rag_ingestion(ctx: dict, *, campaign_id: str):
    """
    ARQ task: ingest a generated campaign into the RAG knowledge base.
    """
    logger.info(f"[WORKER] Starting RAG ingestion for campaign {campaign_id}")
    from backend.app.db.base import SessionLocal
    from backend.app.db.models import GeneratedCampaign
    from backend.app.services.rag_service import get_rag_service

    async def _ingest_once() -> None:
        db = SessionLocal()
        try:
            gc = db.get(GeneratedCampaign, _uuid.UUID(campaign_id))
            if gc:
                rag = get_rag_service(db)
                await rag.ingest_campaign(gc)
                logger.info(f"[WORKER] ✅ RAG ingestion complete for {campaign_id}")
            else:
                logger.warning(f"[WORKER] Campaign {campaign_id} not found for RAG ingestion")
        finally:
            db.close()

    await _execute_with_resilience(
        job_id=None,
        circuit_name="rag_ingestion",
        operation_name="rag_ingestion",
        coro_factory=_ingest_once,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ARQ WorkerSettings — this is what `arq` reads on boot
# ─────────────────────────────────────────────────────────────────────────────

class WorkerSettings:
    """ARQ worker configuration."""

    # Map of task function names → callables
    functions = [
        run_media_render,
        run_generic_job,
        run_rag_ingestion,
    ]

    # Redis connection
    redis_settings = _get_redis_settings()

    # Concurrency: how many tasks run in parallel per worker
    max_jobs = _worker_settings().WORKER_MAX_JOBS

    # If a media render takes too long, ARQ marks it timed out.
    job_timeout = _worker_settings().WORKER_JOB_TIMEOUT_SECONDS

    # Retries at worker level. Actual defer timing is handled by Retry(defer=...)
    max_tries = _worker_settings().WORKER_MAX_TRIES

    # Health check interval
    health_check_interval = 30

    # Queue name
    queue_name = "catalyst:queue"

    on_startup = None
    on_shutdown = None
