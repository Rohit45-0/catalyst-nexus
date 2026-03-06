from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from backend.app.services.search_service import get_search_service, SearchService
from backend.app.core.security import get_current_user
from backend.app.db.models import User

router = APIRouter()

@router.post("/", response_model=List[Dict[str, str]])
async def perform_search(
    query: str = Query(..., min_length=2),
    max_results: int = Query(6, ge=1, le=20),
    service: SearchService = Depends(get_search_service),
    current_user: User = Depends(get_current_user),
):
    """
    Perform a web search using the configured provider.
    """
    return await service.search(query, max_results)
