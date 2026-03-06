from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
import structlog
import io
import csv

from backend.app.core.security import get_current_user
from backend.app.db.base import get_db
from backend.app.db.models import User
from backend.app.services.rag_service import get_rag_service

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.post("/{project_id}/knowledge", status_code=status.HTTP_201_CREATED)
async def upload_business_knowledge(
    project_id: UUID,
    text_content: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db)
):
    """
    Upload textual knowledge (menus, FAQs, price lists) for the WhatsApp RAG bot.
    Accepts either raw text_content or a .txt / .csv file upload.
    """
    if not text_content and not file:
        raise HTTPException(status_code=400, detail="Must provide either text_content or a file.")

    rag_service = get_rag_service(db)
    extracted_text = ""

    # 1. Process Raw Text
    if text_content:
        extracted_text += text_content + "\n\n"

    # 2. Process File Upload
    if file:
        content = await file.read()
        
        # Determine file type
        if file.filename.endswith(".csv"):
            try:
                # Convert CSV to readable text format for RAG
                decoded_content = content.decode("utf-8")
                csv_reader = csv.reader(io.StringIO(decoded_content))
                headers = next(csv_reader, None)
                if headers:
                    extracted_text += f"Data from {file.filename}:\n"
                    for row in csv_reader:
                        row_dict = dict(zip(headers, row))
                        row_text = ", ".join([f"{k}: {v}" for k, v in row_dict.items()])
                        extracted_text += f"- {row_text}\n"
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")
        
        elif file.filename.endswith(".txt"):
            extracted_text += content.decode("utf-8")
        else:
            raise HTTPException(status_code=400, detail="Currently only .txt and .csv files are supported for knowledge ingest.")

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="No valid text could be extracted.")

    # 3. Ingest into pgvector via RAG Service
    try:
        from backend.app.db.models import KnowledgeChunk
        # We chunk it roughly into paragraphs or lines to avoid exceeding embed limits
        chunks = [c.strip() for c in extracted_text.split("\n\n") if len(c.strip()) > 10]
        
        ingested = 0
        for text_chunk in chunks:
            try:
                embedding = await rag_service.generate_embedding(text_chunk)
                new_chunk = KnowledgeChunk(
                    user_id=current_user.id,
                    project_id=project_id,
                    content=text_chunk,
                    embedding=embedding,
                    category="whatsapp_knowledge",
                    source_type="user_upload",
                    confidence_score=1.0
                )
                db.add(new_chunk)
                ingested += 1
            except Exception as e:
                logger.warning(f"Failed to ingest chunk: {e}")

        db.commit()
        return {"status": "success", "message": f"Ingested {ingested} knowledge chunks extracted from input."}

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save RAG knowledge: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save knowledge to vector database.")
