"""
Storage Service - Abstraction layer for local and GCS storage backends
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from google.api_core import exceptions
from google.cloud import storage
from google.cloud.storage.retry import DEFAULT_RETRY

logger = logging.getLogger(__name__)


class StorageUploadError(Exception):
    """Raised when GCS upload fails after retries"""
    pass


class StorageService:
    """Abstraction layer for audio file storage with local and GCS backends"""
    
    def __init__(
        self,
        backend: str = "local",
        local_dir: Optional[Path] = None,
        gcs_bucket_name: Optional[str] = None,
        gcs_project_id: Optional[str] = None,
    ):
        """
        Initialize storage service
        
        Args:
            backend: "local" or "gcs"
            local_dir: Directory for local storage (default: audio_output)
            gcs_bucket_name: GCS bucket name (required for gcs backend)
            gcs_project_id: GCP project ID (optional, uses ADC if not provided)
        """
        self.backend = backend.lower()
        self.local_dir = Path(local_dir or "audio_output")
        self.local_dir.mkdir(exist_ok=True, parents=True)
        
        # GCS configuration
        self.gcs_bucket_name = gcs_bucket_name
        self.gcs_project_id = gcs_project_id
        self.gcs_client: Optional[storage.Client] = None
        self.gcs_bucket: Optional[storage.Bucket] = None
        
        # Configure custom retry policy with exponential backoff
        self.gcs_retry = DEFAULT_RETRY.with_timeout(300.0).with_delay(
            initial=1.0,
            multiplier=2.0,
            maximum=60.0
        )
        
        if self.backend == "gcs":
            self._initialize_gcs()
    
    def _initialize_gcs(self):
        """Initialize GCS client and bucket"""
        if not self.gcs_bucket_name:
            raise ValueError("gcs_bucket_name is required for GCS backend")
        
        try:
            # Use Application Default Credentials (ADC) - automatic on Cloud Run
            self.gcs_client = storage.Client(project=self.gcs_project_id)
            self.gcs_bucket = self.gcs_client.bucket(self.gcs_bucket_name)
            logger.info(
                f"Initialized GCS storage: bucket={self.gcs_bucket_name}, "
                f"project={self.gcs_project_id or 'default'}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            raise StorageUploadError(f"GCS initialization failed: {e}")
    
    def upload_audio_file(
        self,
        local_path: Path,
        remote_name: str,
        language: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Upload audio file to configured storage backend
        
        Args:
            local_path: Path to local audio file
            remote_name: Destination filename (e.g., "news_abc_en.mp3")
            language: Language code for metadata
            metadata: Additional metadata dict
            
        Returns:
            str: Public URL for GCS backend, local path for local backend
            
        Raises:
            StorageUploadError: If GCS upload fails after retries
        """
        if self.backend == "local":
            return self._upload_local(local_path, remote_name)
        elif self.backend == "gcs":
            return self._upload_gcs(local_path, remote_name, language, metadata)
        else:
            raise ValueError(f"Unknown storage backend: {self.backend}")
    
    def _upload_local(self, local_path: Path, remote_name: str) -> str:
        """Upload to local filesystem (no-op, file already exists)"""
        # For local backend, file is already in the right place
        # Just return the path
        return str(local_path)
    
    def _upload_gcs(
        self,
        local_path: Path,
        remote_name: str,
        language: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Upload audio file to Google Cloud Storage
        
        Uses exponential backoff retry and checks for existing files (idempotency)
        """
        if not self.gcs_bucket:
            raise StorageUploadError("GCS bucket not initialized")
        
        if not local_path.exists():
            raise StorageUploadError(f"Local file not found: {local_path}")
        
        # Store under audio/ prefix for lifecycle management
        blob_name = f"audio/{remote_name}"
        blob = self.gcs_bucket.blob(blob_name)
        
        try:
            # Check if file already exists (idempotency for retries)
            if blob.exists(retry=self.gcs_retry):
                logger.info(f"File already exists in GCS, skipping upload: {blob_name}")
                return self.get_public_url(remote_name)
            
            # Prepare metadata
            file_size = local_path.stat().st_size
            upload_metadata = {
                "generated_at": datetime.utcnow().isoformat(),
                "file_size": str(file_size),
            }
            if language:
                upload_metadata["language"] = language
            if metadata:
                upload_metadata.update(metadata)
            
            blob.metadata = upload_metadata
            
            # Upload with retry logic
            logger.info(f"Uploading to GCS: {blob_name} ({file_size} bytes)")
            blob.upload_from_filename(
                local_path,
                content_type="audio/mpeg",
                retry=self.gcs_retry,
            )
            
            public_url = self.get_public_url(remote_name)
            logger.info(f"Successfully uploaded to GCS: {public_url}")
            return public_url
            
        except (
            exceptions.TooManyRequests,
            exceptions.InternalServerError,
            exceptions.BadGateway,
            exceptions.ServiceUnavailable,
        ) as e:
            error_msg = f"GCS upload failed after retries: {type(e).__name__}: {e}"
            logger.error(error_msg)
            raise StorageUploadError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected GCS upload error: {type(e).__name__}: {e}"
            logger.error(error_msg)
            raise StorageUploadError(error_msg)
    
    def get_public_url(self, remote_name: str) -> str:
        """
        Get public URL for an audio file
        
        Args:
            remote_name: Filename (e.g., "news_abc_en.mp3")
            
        Returns:
            str: Public URL (GCS) or local path (local backend)
        """
        if self.backend == "gcs":
            blob_name = f"audio/{remote_name}"
            return f"https://storage.googleapis.com/{self.gcs_bucket_name}/{blob_name}"
        else:
            return str(self.local_dir / remote_name)
    
    def delete_local_file(self, local_path: Path) -> bool:
        """
        Delete local file after successful upload
        
        Args:
            local_path: Path to local file
            
        Returns:
            bool: True if deleted, False otherwise
        """
        try:
            if local_path.exists():
                local_path.unlink()
                logger.debug(f"Deleted local file: {local_path}")
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to delete local file {local_path}: {e}")
            return False
