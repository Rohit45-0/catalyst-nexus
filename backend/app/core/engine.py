"""
Task Engine
===========

Main task routing logic for job processing and orchestration.
"""

from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
import asyncio
import uuid

import structlog
from sqlalchemy import select

from backend.app.agents.orchestrator import NexusOrchestrator
from backend.app.db.schemas import JobStatus
from backend.app.db.base import SessionLocal
from backend.app.db.models import Job

logger = structlog.get_logger(__name__)


class TaskEngine:
    """
    Central task engine for routing and managing AI generation jobs.

    This engine coordinates job execution, handles cancellation,
    and manages the job lifecycle.
    """

    def __init__(self):
        """Initialize the task engine."""
        self.orchestrator = NexusOrchestrator()
        self._active_jobs: Dict[str, asyncio.Task] = {}
        logger.info("Task Engine initialized")

    async def _is_cancelled(self, job_id: str) -> bool:
        """Check if a job has been cancelled via Redis."""
        try:
            from backend.app.core.redis import get_redis
            r = await get_redis()
            return await r.exists(f"catalyst:cancelled_job:{job_id}") == 1
        except Exception as e:
            logger.error(f"Failed to check cancel flag in Redis: {e}")
            return False

    async def process_job(
        self,
        job_id: str,
        job_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a generation job.

        Args:
            job_id: Unique identifier for the job.
            job_type: Type of job to process.
            parameters: Job parameters.

        Returns:
            dict: Job result including output assets and metadata.
        """
        logger.info("Processing job", job_id=job_id, job_type=job_type)

        # Track local task to allow forced cancellation if running in this worker
        try:
            self._active_jobs[job_id] = asyncio.current_task()
        except RuntimeError:
            pass

        # Check if job was cancelled before starting
        if await self._is_cancelled(job_id):
            return {
                "status": JobStatus.CANCELLED.value,
                "message": "Job was cancelled before processing started",
            }

        await self._update_job_status(
            job_id,
            status=JobStatus.RUNNING,
            message="Job started",
            started_at=datetime.utcnow(),
            progress=5,
        )

        try:
            run_inputs = self._build_run_inputs(job_type, parameters)

            # Execute orchestrator workflow
            result = await self.orchestrator.run(
                workflow_type=run_inputs["workflow_type"],
                project_id=run_inputs["project_id"],
                product_name=run_inputs["product_name"],
                product_images=run_inputs["product_images"],
                duration_seconds=run_inputs["duration_seconds"],
                aspect_ratio=run_inputs["aspect_ratio"],
                job_id=job_id,
                **run_inputs["extra"],
            )

            # Check if cancelled during execution
            if await self._is_cancelled(job_id):
                await self._update_job_status(
                    job_id,
                    status=JobStatus.CANCELLED,
                    message="Job cancelled during execution",
                )
                return {"status": JobStatus.CANCELLED.value}

            errors = result.get("errors") or []
            failed = bool(errors) or result.get("status") == "failed"
            final_status = JobStatus.FAILED if failed else JobStatus.COMPLETED
            error_message = "; ".join(errors) if errors else None

            stage_messages = result.get("stage_messages") or []
            status_message = stage_messages[-1] if stage_messages else "Completed"
            progress = int(result.get("progress_percent", 100 if not failed else 100))

            output_assets = []
            if result.get("video_url"):
                output_assets.append(result["video_url"])
            if result.get("thumbnail_url"):
                output_assets.append(result["thumbnail_url"])

            await self._update_job_status(
                job_id,
                status=final_status,
                message=status_message,
                completed_at=datetime.utcnow(),
                result=result,
                output_assets=output_assets,
                error=error_message,
                progress=progress,
            )

            logger.info(
                "Job completed",
                job_id=job_id,
                status=final_status.value,
                output_count=len(output_assets),
            )
            return result

        except Exception as e:
            logger.error("Job failed", job_id=job_id, error=str(e))
            await self._update_job_status(
                job_id,
                status=JobStatus.FAILED,
                message=f"Job failed: {str(e)}",
                completed_at=datetime.utcnow(),
                error=str(e),
                progress=100,
            )
            return {"status": JobStatus.FAILED.value, "error": str(e)}

        finally:
            self._active_jobs.pop(job_id, None)

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running or pending job.

        Args:
            job_id: The job ID to cancel.

        Returns:
            bool: True if cancellation was requested successfully.
        """
        logger.info("Cancellation requested", job_id=job_id)
        
        # Set cancel flag in Redis (expires in 24 hours)
        try:
            from backend.app.core.redis import get_redis
            r = await get_redis()
            await r.setex(f"catalyst:cancelled_job:{job_id}", 86400, "1")
        except Exception as e:
            logger.error(f"Failed to set cancel flag in Redis: {e}")

        # If it happens to be running on this exact instance, cancel the task
        if job_id in self._active_jobs:
            task = self._active_jobs[job_id]
            task.cancel()
            return True

        return True

    async def get_job_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current progress of a job.

        Args:
            job_id: The job ID to check.

        Returns:
            dict: Progress information or None if not found.
        """
        status = self.orchestrator.get_status(job_id)
        if status:
            return {
                "progress": int(status.get("progress_percent", 0)),
                "current_step": status.get("current_stage", "unknown"),
                "message": (status.get("stage_messages") or [""])[-1],
            }
        return None

    def _build_run_inputs(self, job_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize API job payload into orchestrator.run inputs."""
        params = parameters or {}

        workflow_type = str(params.get("workflow_type") or job_type or "full_pipeline")
        project_id = str(params.get("project_id") or params.get("projectId") or "unknown-project")
        product_name = str(params.get("product_name") or params.get("prompt") or "Generated Product")

        images = params.get("product_images") or params.get("image_urls") or params.get("reference_images") or []
        if isinstance(images, str):
            images = [images]
        if not isinstance(images, list):
            images = []

        duration_raw = params.get("duration_seconds", params.get("duration", 15.0))
        try:
            duration_seconds = float(duration_raw)
        except (TypeError, ValueError):
            duration_seconds = 15.0

        aspect_ratio = str(params.get("aspect_ratio") or "16:9")

        passthrough_keys = {
            "brand_guidelines",
            "target_audience",
            "video_style",
            "quality",
            "seed",
            "auto_publish",
            "publish_to_platforms",
            "publish_caption",
        }
        extra = {k: v for k, v in params.items() if k in passthrough_keys}

        return {
            "workflow_type": workflow_type,
            "project_id": project_id,
            "product_name": product_name,
            "product_images": images,
            "duration_seconds": duration_seconds,
            "aspect_ratio": aspect_ratio,
            "extra": extra,
        }

    async def _update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        message: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        result: Optional[Dict[str, Any]] = None,
        output_assets: Optional[list] = None,
        error: Optional[str] = None,
        progress: Optional[int] = None,
    ):
        """
        Update job status in the database.
        """
        db = SessionLocal()
        try:
            try:
                lookup_id = uuid.UUID(job_id)
            except ValueError:
                lookup_id = job_id

            job = db.get(Job, lookup_id)
            if not job:
                return

            job.status = status.value if isinstance(status, JobStatus) else str(status)
            job.status_message = message

            if started_at:
                job.started_at = started_at
            if completed_at:
                job.completed_at = completed_at
            if result is not None:
                job.result = result
                job.output_payload = result
            if output_assets is not None:
                job.output_assets = output_assets
            if error:
                job.error = error
            if progress is not None:
                job.progress = max(0, min(100, int(progress)))

            db.commit()
            
            # Broadcast the update via Redis Pub/Sub (works across all worker/API nodes)
            from backend.app.core.redis import publish_job_update
            await publish_job_update(str(job_id), {
                "job_id": str(job_id),
                "status": job.status,
                "message": job.status_message,
                "progress": job.progress,
                "error": job.error,
                "result": job.result,
                "output_assets": job.output_assets,
            })
            
        except Exception as e:
            db.rollback()
            logger.error("Failed to update job status", job_id=job_id, error=str(e))
        finally:
            db.close()

    async def retry_failed_jobs(self, max_age_hours: int = 24) -> int:
        """
        Retry all failed jobs within the specified time window.
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        retry_count = 0

        db = SessionLocal()
        try:
            query = select(Job).where(
                Job.status == JobStatus.FAILED.value,
                Job.created_at >= cutoff,
                Job.retry_count < 3,
            )
            failed_jobs = db.execute(query).scalars().all()

            for job in failed_jobs:
                job.status = JobStatus.PENDING.value
                job.retry_count = (job.retry_count or 0) + 1
                job.error = None
                job.started_at = None
                job.completed_at = None
                retry_count += 1

                try:
                    from arq.connections import create_pool
                    from backend.app.core.redis import get_arq_redis_settings
                    pool = await create_pool(get_arq_redis_settings())
                    await pool.enqueue_job(
                        "run_generic_job",
                        job_id=str(job.id),
                        job_type=job.job_type,
                        parameters=job.parameters or {},
                    )
                    await pool.aclose()
                except Exception as e:
                    logger.error("Failed to enqueue retried job to Redis", error=str(e))

            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        logger.info("Queued jobs for retry", count=retry_count)
        return retry_count

    async def cleanup_stale_jobs(self, stale_threshold_minutes: int = 60) -> int:
        """
        Clean up jobs that have been running too long without updates.
        """
        cutoff = datetime.utcnow() - timedelta(minutes=stale_threshold_minutes)
        cleanup_count = 0

        db = SessionLocal()
        try:
            query = select(Job).where(
                Job.status == JobStatus.RUNNING.value,
                Job.started_at < cutoff,
            )
            stale_jobs = db.execute(query).scalars().all()

            for job in stale_jobs:
                job.status = JobStatus.FAILED.value
                job.error = "Job timed out - exceeded maximum processing time"
                job.completed_at = datetime.utcnow()
                cleanup_count += 1

            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        if cleanup_count > 0:
            logger.warning("Cleaned stale jobs", count=cleanup_count)

        return cleanup_count
