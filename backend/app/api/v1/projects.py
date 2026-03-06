"""
Project & Asset Management API Endpoints
========================================

Handles CRUD operations for projects and their associated assets,
including images, videos, and generated content.
"""

from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.core.security import get_current_user
from backend.app.db.base import get_db
from backend.app.db.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    AssetCreate,
    AssetResponse,
)
from backend.app.db.models import User, Project, Asset
from backend.app.utils.storage import upload_file, delete_file

router = APIRouter()


# =============================================================================
# Project Endpoints
# =============================================================================

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Create a new project for the authenticated user.
    
    Args:
        project_data: Project creation data.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        ProjectResponse: Created project data.
    """
    new_project = Project(
        name=project_data.name,
        product_name=project_data.name,
        description=project_data.description,
        owner_id=current_user.id,
        settings=project_data.settings or {},
    )
    
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    return new_project


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
):
    """
    List all projects for the authenticated user.
    
    Args:
        current_user: Authenticated user.
        db: Database session.
        skip: Number of records to skip (pagination).
        limit: Maximum number of records to return.
        search: Optional search term for project name.
        
    Returns:
        ProjectListResponse: Paginated list of projects.
    """
    query = select(Project).where(Project.owner_id == current_user.id)
    
    if search:
        query = query.where(Project.name.ilike(f"%{search}%"))
    
    query = query.offset(skip).limit(limit).order_by(Project.created_at.desc())
    
    result = db.execute(query)
    projects = result.scalars().all()
    
    # Get total count
    count_query = select(Project).where(Project.owner_id == current_user.id)
    if search:
        count_query = count_query.where(Project.name.ilike(f"%{search}%"))
    count_result = db.execute(count_query)
    total = len(count_result.scalars().all())
    
    return ProjectListResponse(
        projects=projects,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Get a specific project by ID.
    
    Args:
        project_id: UUID of the project.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        ProjectResponse: Project data.
        
    Raises:
        HTTPException: If project not found or access denied.
    """
    project = db.get(Project, project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )
    
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Update a project's information.
    
    Args:
        project_id: UUID of the project.
        project_update: Fields to update.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        ProjectResponse: Updated project data.
    """
    project = db.get(Project, project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )
    
    update_data = project_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    db.commit()
    db.refresh(project)
    
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Delete a project and all its assets.
    
    Args:
        project_id: UUID of the project.
        current_user: Authenticated user.
        db: Database session.
    """
    project = db.get(Project, project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project"
        )
    
    # Delete associated assets from storage
    for asset in project.assets:
        await delete_file(asset.storage_path)
    
    db.delete(project)
    db.commit()


# =============================================================================
# Asset Endpoints
# =============================================================================

@router.post("/{project_id}/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    project_id: UUID,
    file: UploadFile = File(...),
    asset_type: str = Query(..., regex="^(image|video|audio|document)$"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    """
    Upload an asset to a project.
    
    Args:
        project_id: UUID of the project.
        file: Uploaded file.
        asset_type: Type of asset (image, video, audio, document).
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        AssetResponse: Created asset data.
    """
    project = db.get(Project, project_id)
    
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Upload file to storage
    storage_path = await upload_file(
        file=file,
        folder=f"projects/{project_id}/assets"
    )
    
    # Create asset record
    new_asset = Asset(
        name=file.filename,
        asset_type=asset_type,
        storage_path=storage_path,
        file_size=file.size,
        mime_type=file.content_type,
        project_id=project_id,
    )
    
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    
    return new_asset


@router.get("/{project_id}/assets", response_model=List[AssetResponse])
async def list_assets(
    project_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    asset_type: Optional[str] = None,
):
    """
    List all assets in a project.
    
    Args:
        project_id: UUID of the project.
        current_user: Authenticated user.
        db: Database session.
        asset_type: Optional filter by asset type.
        
    Returns:
        List[AssetResponse]: List of assets.
    """
    project = db.get(Project, project_id)
    
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    query = select(Asset).where(Asset.project_id == project_id)
    
    if asset_type:
        query = query.where(Asset.asset_type == asset_type)
    
    result = db.execute(query)
    assets = result.scalars().all()
    
    return assets


@router.delete("/{project_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    project_id: UUID,
    asset_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """
    Delete an asset from a project.
    
    Args:
        project_id: UUID of the project.
        asset_id: UUID of the asset.
        current_user: Authenticated user.
        db: Database session.
    """
    project = db.get(Project, project_id)
    
    if not project or project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    asset = db.get(Asset, asset_id)
    
    if not asset or asset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    
    # Delete from storage
    await delete_file(asset.storage_path)
    
    db.delete(asset)
    db.commit()
