"""
Firecrawl API Endpoints
========================
Provides web scraping and search via Firecrawl for the
Reference Content analytics section.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl

from backend.app.core.security import get_current_user
from backend.app.db.models import User
from backend.app.services import firecrawl_service

router = APIRouter()


class ScrapeRequest(BaseModel):
    url: str
    formats: list[str] = ["markdown", "metadata"]


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    scrape_content: bool = False


class ScrapeResponse(BaseModel):
    url: str
    markdown: str
    metadata: dict


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_url(
    request: ScrapeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Scrape a URL and return LLM-ready markdown content.
    Useful for extracting full content from YouTube pages, articles, competitor sites.
    """
    try:
        result = firecrawl_service.scrape_url(request.url, request.formats)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Scrape failed: {str(e)}")


@router.post("/search")
async def search_web(
    request: SearchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Search the web using Firecrawl and optionally scrape full page content.
    Returns richer results than Brave — includes full markdown content per page.
    """
    try:
        results = firecrawl_service.search_web(
            query=request.query,
            limit=min(request.limit, 10),
            scrape_content=request.scrape_content,
        )
        return {"results": results, "count": len(results), "query": request.query}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Search failed: {str(e)}")


@router.post("/youtube")
async def extract_youtube(
    request: ScrapeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Extract content from a YouTube video page.
    Returns title, description, and available transcript/metadata.
    """
    if "youtube.com" not in request.url and "youtu.be" not in request.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must be a YouTube video URL"
        )
    try:
        result = firecrawl_service.extract_youtube_content(request.url)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"YouTube extraction failed: {str(e)}")
