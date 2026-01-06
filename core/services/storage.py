"""
Supabase Storage Service for file uploads.

Production-grade file upload handling with validation, error handling,
and proper URL generation for Supabase Storage buckets.
"""

import os
import uuid
from typing import List, Optional, Tuple
from pathlib import Path
from io import BytesIO
import logging

from django.conf import settings
from fastapi import UploadFile, HTTPException, status
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from core.exceptions import ValidationError
from core.choices import MAX_FILE_SIZE_MB, ALLOWED_IMAGE_FORMATS
from core.utils.logger import get_logger

logger = get_logger(__name__)

# Constants
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024  # 5MB
ALLOWED_MIME_TYPES = {
    'image/jpeg': ['jpg', 'jpeg'],
    'image/jpg': ['jpg', 'jpeg'],
    'image/png': ['png'],
    'image/webp': ['webp'],
}


class SupabaseStorageService:
    """
    Service for handling file uploads to Supabase Storage.
    
    Handles:
    - File validation (size, MIME type)
    - Secure uploads with proper paths
    - Public URL generation
    - Error handling and cleanup
    """
    
    def __init__(self):
        """Initialize Supabase client from environment variables."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_service_key:
            raise ValueError(
                "Supabase credentials not configured. "
                "Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables."
            )
        
        # Initialize Supabase client with service role key (has admin access)
        self.client: Client = create_client(
            self.supabase_url,
            self.supabase_service_key,
            options=ClientOptions(
                auto_refresh_token=False,
                persist_session=False
            )
        )
        
        logger.info("Supabase Storage client initialized successfully")
    
    async def _validate_file(self, file: UploadFile) -> Tuple[str, str]:
        """
        Validate uploaded file.
        
        Returns:
            Tuple of (file_extension, mime_type)
        
        Raises:
            ValidationError: If file is invalid
        """
        # Check MIME type
        mime_type = file.content_type
        if mime_type not in ALLOWED_MIME_TYPES:
            raise ValidationError(
                f"Invalid file type: {mime_type}. Allowed types: {', '.join(ALLOWED_MIME_TYPES.keys())}",
                code="INVALID_FILE_TYPE"
            )
        
        # Get file extension from filename
        filename = file.filename or ""
        file_ext = Path(filename).suffix.lower().lstrip('.')
        
        # Validate extension matches MIME type
        allowed_extensions = ALLOWED_MIME_TYPES.get(mime_type, [])
        if file_ext not in allowed_extensions and file_ext not in ALLOWED_IMAGE_FORMATS:
            raise ValidationError(
                f"File extension '{file_ext}' does not match MIME type '{mime_type}'",
                code="INVALID_FILE_EXTENSION"
            )
        
        # Validate file size - read content to check size
        file_content = await file.read()
        file_size = len(file_content)
        
        # Reset file pointer for actual upload
        await file.seek(0)
        
        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValidationError(
                f"File size ({file_size / 1024 / 1024:.2f} MB) exceeds maximum allowed size ({MAX_FILE_SIZE_MB} MB)",
                code="FILE_TOO_LARGE"
            )
        
        if file_size == 0:
            raise ValidationError("File is empty", code="EMPTY_FILE")
        
        return file_ext, mime_type
    
    def _generate_file_path(self, bucket: str, user_id: int, filename: str) -> str:
        """
        Generate secure file path in Supabase Storage.
        
        Format: {bucket}/{user_id}/{uuid}_{filename}
        
        Args:
            bucket: Supabase bucket name
            user_id: User ID for organization
            filename: Original filename
        
        Returns:
            Storage path string
        """
        # Generate unique filename to prevent collisions
        unique_id = uuid.uuid4().hex[:8]
        safe_filename = f"{unique_id}_{filename}"
        return f"{user_id}/{safe_filename}"
    
    async def upload_file(
        self,
        file: UploadFile,
        bucket: str,
        user_id: int,
        folder: Optional[str] = None
    ) -> str:
        """
        Upload a single file to Supabase Storage.
        
        Args:
            file: FastAPI UploadFile object
            bucket: Supabase bucket name (user-profiles or event-images)
            user_id: User ID for path organization
            folder: Optional subfolder within user_id folder
        
        Returns:
            Public URL of uploaded file
        
        Raises:
            ValidationError: If file validation fails
            HTTPException: If upload fails
        """
        # Validate file and get content
        file_ext, mime_type = await self._validate_file(file)
        
        # Generate storage path
        filename = file.filename or f"upload.{file_ext}"
        if folder:
            storage_path = f"{user_id}/{folder}/{uuid.uuid4().hex[:8]}_{filename}"
        else:
            storage_path = self._generate_file_path(bucket, user_id, filename)
        
        try:
            # Read file content (file pointer already at start after validation)
            file_content = await file.read()
            
            # Upload to Supabase Storage
            response = self.client.storage.from_(bucket).upload(
                path=storage_path,
                file=file_content,
                file_options={
                    "content-type": mime_type,
                    "upsert": "false"  # Don't overwrite existing files
                }
            )
            
            # Check for errors in response
            if hasattr(response, 'error') and response.error:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload file to Supabase: {response.error}"
                )
            
            # Get public URL
            public_url = self.client.storage.from_(bucket).get_public_url(storage_path)
            
            logger.info(f"File uploaded successfully: {storage_path} to bucket {bucket}")
            return public_url
            
        except ValidationError:
            raise
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading file to Supabase Storage: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(e)}"
            )
    
    async def upload_multiple_files(
        self,
        files: List[UploadFile],
        bucket: str,
        user_id: int,
        folder: Optional[str] = None
    ) -> List[str]:
        """
        Upload multiple files to Supabase Storage.
        
        Args:
            files: List of FastAPI UploadFile objects
            bucket: Supabase bucket name
            user_id: User ID for path organization
            folder: Optional subfolder
        
        Returns:
            List of public URLs
        
        Raises:
            ValidationError: If any file validation fails
        """
        uploaded_urls = []
        failed_uploads = []
        
        for idx, file in enumerate(files):
            try:
                url = await self.upload_file(file, bucket, user_id, folder)
                uploaded_urls.append(url)
            except Exception as e:
                logger.error(f"Failed to upload file {idx + 1}: {str(e)}")
                failed_uploads.append(idx + 1)
                # Continue uploading other files
        
        if failed_uploads:
            raise ValidationError(
                f"Failed to upload {len(failed_uploads)} file(s). Please check file formats and sizes.",
                code="UPLOAD_FAILED",
                details={"failed_indices": failed_uploads}
            )
        
        return uploaded_urls
    
    def delete_file(self, bucket: str, file_path: str) -> bool:
        """
        Delete a file from Supabase Storage.
        
        Args:
            bucket: Supabase bucket name
            file_path: Full storage path to file
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            response = self.client.storage.from_(bucket).remove([file_path])
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Error deleting file from Supabase: {response.error}")
                return False
            
            logger.info(f"File deleted successfully: {file_path} from bucket {bucket}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file from Supabase Storage: {str(e)}", exc_info=True)
            return False


# Singleton instance
_storage_service: Optional[SupabaseStorageService] = None


def get_storage_service() -> SupabaseStorageService:
    """Get or create Supabase Storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = SupabaseStorageService()
    return _storage_service

