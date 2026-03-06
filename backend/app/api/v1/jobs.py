"""
Job Management API Endpoints
============================

Handles AI generation job creation, status tracking, and result retrieval.
Jobs represent async tasks like video generation, identity extraction, etc.
"""

from typing import Annotated, List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.core.security import get_current_user
from backend.app.core.engine import TaskEngine
from backend.app.db.base import get_db
from backend.app.db.schemas import (
    JobCreate,
    JobResponse,
    JobListResponse,
    JobStatus,
)
from backend.app.db.models import User, Job, Project

router = APIRouter()
task_engine = TaskEngine()


@router.post("/generate", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_generation_job(
    job_data: JobCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Create a new AI generation job.
    
    Supported job types:
    - identity_extraction: Extract identity features from images
    - video_generation: Generate video from prompts and identities
    - motion_transfer: Apply motion to static images
    - style_transfer: Apply artistic styles to content
    
    Args:
        job_data: Job creation parameters.
        background_tasks: FastAPI background tasks.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        JobResponse: Created job with status 'pending'.
    """
    # Verify project access
    project = None
    if job_data.project_id:
        project = db.get(Project, job_data.project_id)
        if not project or project.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

    job_parameters = dict(job_data.parameters or {})
    if job_data.project_id:
        job_parameters.setdefault("project_id", str(job_data.project_id))
    if project and project.product_name:
        job_parameters.setdefault("product_name", project.product_name)
    if project and project.image_path:
        job_parameters.setdefault("product_images", [project.image_path])
    
    # Create job record
    new_job = Job(
        job_type=job_data.job_type,
        status=JobStatus.PENDING.value,
        parameters=job_parameters,
        project_id=job_data.project_id,
        user_id=current_user.id,
        priority=job_data.priority or 5,
    )
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # Queue the job for processing via Redis/ARQ
    try:
        from backend.app.core.redis import enqueue_media_render
        from arq.connections import create_pool
        from backend.app.core.redis import get_arq_redis_settings
        pool = await create_pool(get_arq_redis_settings())
        await pool.enqueue_job(
            "run_generic_job",
            job_id=str(new_job.id),
            job_type=new_job.job_type,
            parameters=new_job.parameters,
        )
        await pool.aclose()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to enqueue job to Redis: {e}")
    
    return new_job


@router.get("", response_model=JobListResponse)
async def list_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[JobStatus] = None,
    project_id: Optional[UUID] = None,
):
    """
    List all jobs for the authenticated user.
    
    Args:
        current_user: Authenticated user.
        db: Database session.
        skip: Pagination offset.
        limit: Maximum results.
        status_filter: Filter by job status.
        project_id: Filter by project.
        
    Returns:
        JobListResponse: Paginated list of jobs.
    """
    query = select(Job).where(Job.user_id == current_user.id)
    
    if status_filter:
        query = query.where(Job.status == status_filter.value)
    
    if project_id:
        query = query.where(Job.project_id == project_id)
    
    query = query.offset(skip).limit(limit).order_by(Job.created_at.desc())
    
    result = db.execute(query)
    jobs = result.scalars().all()
    
    # Get total count
    count_query = select(Job).where(Job.user_id == current_user.id)
    if status_filter:
        count_query = count_query.where(Job.status == status_filter.value)
    if project_id:
        count_query = count_query.where(Job.project_id == project_id)
    count_result = db.execute(count_query)
    total = len(count_result.scalars().all())
    
    return JobListResponse(
        jobs=jobs,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific job.
    
    Args:
        job_id: UUID of the job.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        JobResponse: Job details including status and results.
    """
    job = db.get(Job, job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this job"
        )
    
    return job


@router.get("/{job_id}/status")
async def get_job_status(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Get the current status of a job (lightweight endpoint for polling).
    
    Args:
        job_id: UUID of the job.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        dict: Job status and progress information.
    """
    job = db.get(Job, job_id)
    
    if not job or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return {
        "job_id": str(job.id),
        "status": job.status,
        "progress": job.progress,
        "message": job.status_message,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Cancel a pending or running job.
    
    Args:
        job_id: UUID of the job.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        JobResponse: Updated job with cancelled status.
    """
    job = db.get(Job, job_id)
    
    if not job or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status}"
        )
    
    job.status = JobStatus.CANCELLED.value
    job.completed_at = datetime.utcnow()
    job.status_message = "Cancelled by user"
    
    # Signal the task engine to stop processing
    await task_engine.cancel_job(str(job_id))
    
    db.commit()
    db.refresh(job)
    
    return job


@router.post("/{job_id}/retry", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_job(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Retry a failed or cancelled job.
    
    Args:
        job_id: UUID of the job.
        background_tasks: FastAPI background tasks.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        JobResponse: Job with reset status.
    """
    job = db.get(Job, job_id)
    
    if not job or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status not in [JobStatus.FAILED.value, JobStatus.CANCELLED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only retry failed or cancelled jobs"
        )
    
    # Reset job state
    job.status = JobStatus.PENDING.value
    job.progress = 0
    job.error = None
    job.result = None
    job.started_at = None
    job.completed_at = None
    job.status_message = "Retry requested"
    job.retry_count = (job.retry_count or 0) + 1
    
    db.commit()
    db.refresh(job)
    
    # Re-queue for processing via Redis/ARQ
    try:
        from arq.connections import create_pool
        from backend.app.core.redis import get_arq_redis_settings
        pool = await create_pool(get_arq_redis_settings())
        await pool.enqueue_job(
            "run_generic_job",
            job_id=str(job.id),
            job_type=job.job_type,
            parameters=job.parameters,
        )
        await pool.aclose()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to enqueue retry job to Redis: {e}")
    
    return job


@router.get("/{job_id}/result")
async def get_job_result(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Get the result of a completed job.
    
    Args:
        job_id: UUID of the job.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        dict: Job result data including output URLs.
    """
    job = db.get(Job, job_id)
    
    if not job or job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status != JobStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed. Current status: {job.status}"
        )
    
    return {
        "job_id": str(job.id),
        "job_type": job.job_type,
        "result": job.result,
        "output_assets": job.output_assets,
        "completed_at": job.completed_at,
        "processing_time_seconds": (
            (job.completed_at - job.started_at).total_seconds()
            if job.completed_at and job.started_at else None
        ),
    }


@router.websocket("/{job_id}/ws")
async def job_tracking_websocket(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time tracking of a specific job.
    """
    from backend.app.core.websocket import manager
    
    # Accept the connection
    await manager.connect(websocket, job_id)
    
    try:
        # Keep the connection alive
        while True:
            # We don't expect messages from the client, just keep the socket open
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)
    except Exception as e:
        manager.disconnect(websocket, job_id)
