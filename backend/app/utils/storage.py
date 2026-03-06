"""
Storage Utilities
=================

Multi-backend storage helpers for S3, Supabase, and local filesystem.
"""

from typing import Optional, BinaryIO
from pathlib import Path
import uuid
import asyncio
import structlog

from fastapi import UploadFile
import aioboto3

from backend.app.core.config import settings

logger = structlog.get_logger(__name__)


class StorageBackend:
    """Base class for storage backends."""
    
    async def upload(
        self,
        file: BinaryIO,
        path: str,
        content_type: Optional[str] = None
    ) -> str:
        """Upload a file and return its path/URL."""
        raise NotImplementedError
    
    async def download(self, path: str) -> bytes:
        """Download a file and return its contents."""
        raise NotImplementedError
    
    async def delete(self, path: str) -> bool:
        """Delete a file. Returns True if successful."""
        raise NotImplementedError
    
    async def get_url(self, path: str, expires_in: int = 3600) -> str:
        """Get a (possibly signed) URL for the file."""
        raise NotImplementedError
    
    async def exists(self, path: str) -> bool:
        """Check if a file exists."""
        raise NotImplementedError


class S3Storage(StorageBackend):
    """AWS S3 storage backend."""
    
    def __init__(self):
        self.bucket = settings.AWS_S3_BUCKET
        self.region = settings.AWS_REGION
        self.session = aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=self.region,
        )
    
    async def upload(
        self,
        file: BinaryIO,
        path: str,
        content_type: Optional[str] = None
    ) -> str:
        async with self.session.client('s3') as s3:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            await s3.upload_fileobj(
                file,
                self.bucket,
                path,
                ExtraArgs=extra_args
            )
        
        logger.info("Uploaded to S3", path=path)
        return path
    
    async def download(self, path: str) -> bytes:
        async with self.session.client('s3') as s3:
            response = await s3.get_object(Bucket=self.bucket, Key=path)
            return await response['Body'].read()
    
    async def delete(self, path: str) -> bool:
        try:
            async with self.session.client('s3') as s3:
                await s3.delete_object(Bucket=self.bucket, Key=path)
            logger.info("Deleted from S3", path=path)
            return True
        except Exception as e:
            logger.error("Failed to delete from S3", path=path, error=str(e))
            return False
    
    async def get_url(self, path: str, expires_in: int = 3600) -> str:
        async with self.session.client('s3') as s3:
            url = await s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': path},
                ExpiresIn=expires_in
            )
        return url
    
    async def exists(self, path: str) -> bool:
        try:
            async with self.session.client('s3') as s3:
                await s3.head_object(Bucket=self.bucket, Key=path)
            return True
        except:
            return False


class LocalStorage(StorageBackend):
    """Local filesystem storage backend."""
    
    def __init__(self, base_path: str = "./storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def upload(
        self,
        file: BinaryIO,
        path: str,
        content_type: Optional[str] = None
    ) -> str:
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._write_file,
            full_path,
            file.read()
        )
        
        logger.info("Uploaded to local storage", path=path)
        return path
    
    def _write_file(self, path: Path, content: bytes):
        with open(path, 'wb') as f:
            f.write(content)
    
    async def download(self, path: str) -> bytes:
        full_path = self.base_path / path
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._read_file,
            full_path
        )
    
    def _read_file(self, path: Path) -> bytes:
        with open(path, 'rb') as f:
            return f.read()
    
    async def delete(self, path: str) -> bool:
        full_path = self.base_path / path
        try:
            full_path.unlink(missing_ok=True)
            logger.info("Deleted from local storage", path=path)
            return True
        except Exception as e:
            logger.error("Failed to delete from local storage", path=path, error=str(e))
            return False
    
    async def get_url(self, path: str, expires_in: int = 3600) -> str:
        # For local storage, return the file path
        return str(self.base_path / path)
    
    async def exists(self, path: str) -> bool:
        return (self.base_path / path).exists()


class SupabaseStorage(StorageBackend):
    """Supabase storage backend."""
    
    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
        self._client = None
    
    async def _get_client(self):
        if self._client is None:
            from supabase import create_client
            self._client = create_client(self.url, self.key)
        return self._client
    
    async def upload(
        self,
        file: BinaryIO,
        path: str,
        content_type: Optional[str] = None
    ) -> str:
        client = await self._get_client()
        
        # Extract bucket and file path
        parts = path.split('/', 1)
        bucket = parts[0] if len(parts) > 1 else 'default'
        file_path = parts[1] if len(parts) > 1 else parts[0]
        
        content = file.read()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: client.storage.from_(bucket).upload(
                file_path,
                content,
                file_options={"content-type": content_type} if content_type else None
            )
        )
        
        logger.info("Uploaded to Supabase", path=path)
        return path
    
    async def download(self, path: str) -> bytes:
        client = await self._get_client()
        
        parts = path.split('/', 1)
        bucket = parts[0] if len(parts) > 1 else 'default'
        file_path = parts[1] if len(parts) > 1 else parts[0]
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: client.storage.from_(bucket).download(file_path)
        )
    
    async def delete(self, path: str) -> bool:
        try:
            client = await self._get_client()
            
            parts = path.split('/', 1)
            bucket = parts[0] if len(parts) > 1 else 'default'
            file_path = parts[1] if len(parts) > 1 else parts[0]
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: client.storage.from_(bucket).remove([file_path])
            )
            
            logger.info("Deleted from Supabase", path=path)
            return True
        except Exception as e:
            logger.error("Failed to delete from Supabase", path=path, error=str(e))
            return False
    
    async def get_url(self, path: str, expires_in: int = 3600) -> str:
        client = await self._get_client()
        
        parts = path.split('/', 1)
        bucket = parts[0] if len(parts) > 1 else 'default'
        file_path = parts[1] if len(parts) > 1 else parts[0]
        
        return client.storage.from_(bucket).create_signed_url(file_path, expires_in)['signedURL']
    
    async def exists(self, path: str) -> bool:
        try:
            await self.download(path)
            return True
        except:
            return False


def get_storage_backend() -> StorageBackend:
    """
    Get the configured storage backend.
    
    Returns the appropriate storage backend based on settings.
    """
    backend_type = settings.storage_backend
    
    if backend_type == "s3":
        return S3Storage()
    elif backend_type == "supabase":
        return SupabaseStorage()
    else:
        return LocalStorage()


# Global storage instance
_storage: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """Get the global storage instance."""
    global _storage
    if _storage is None:
        _storage = get_storage_backend()
    return _storage


async def upload_file(
    file: UploadFile,
    folder: str = "",
    filename: Optional[str] = None,
) -> str:
    """
    Upload a file to storage.
    
    Args:
        file: The uploaded file.
        folder: Destination folder path.
        filename: Optional custom filename. If None, generates UUID-based name.
        
    Returns:
        The storage path of the uploaded file.
    """
    storage = get_storage()
    
    # Generate filename if not provided
    if filename is None:
        ext = Path(file.filename).suffix if file.filename else ""
        filename = f"{uuid.uuid4().hex}{ext}"
    
    # Construct full path
    path = f"{folder}/{filename}".lstrip("/")
    
    # Upload file
    await storage.upload(
        file=file.file,
        path=path,
        content_type=file.content_type
    )
    
    return path


async def delete_file(path: str) -> bool:
    """
    Delete a file from storage.
    
    Args:
        path: The storage path to delete.
        
    Returns:
        True if deletion was successful.
    """
    if not path:
        return True
    
    storage = get_storage()
    return await storage.delete(path)


async def get_file_url(path: str, expires_in: int = 3600) -> str:
    """
    Get a URL for accessing a file.
    
    Args:
        path: The storage path.
        expires_in: URL expiration time in seconds.
        
    Returns:
        URL to access the file.
    """
    storage = get_storage()
    return await storage.get_url(path, expires_in)
