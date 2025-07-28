"""
Cloud Storage integration for Garak Dashboard API.

This module provides abstraction for storing job data and reports,
supporting both local filesystem (development) and Google Cloud Storage (production).
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List, BinaryIO, TextIO
from datetime import datetime
from pathlib import Path
import tempfile

try:
    from google.cloud import storage
    from google.cloud.exceptions import NotFound, GoogleCloudError
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages file storage for job data and reports."""
    
    def __init__(self):
        """Initialize storage manager with appropriate backend."""
        self.use_gcs = self._should_use_gcs()
        
        if self.use_gcs:
            self._init_gcs()
        else:
            self._init_local()
        
        logger.info(f"Storage manager initialized with {'GCS' if self.use_gcs else 'local filesystem'} backend")
    
    def _should_use_gcs(self) -> bool:
        """Determine if we should use Google Cloud Storage."""
        # Use GCS if we're in a GCP environment and have the library
        return (
            GCS_AVAILABLE and
            (os.environ.get('GOOGLE_CLOUD_PROJECT') or 
             os.environ.get('GCS_REPORTS_BUCKET') or
             os.environ.get('GCS_JOB_DATA_BUCKET'))
        )
    
    def _init_gcs(self):
        """Initialize Google Cloud Storage client."""
        try:
            self.gcs_client = storage.Client()
            self.reports_bucket_name = os.environ.get('GCS_REPORTS_BUCKET', f"{os.environ.get('GOOGLE_CLOUD_PROJECT', 'garak')}-reports")
            self.job_data_bucket_name = os.environ.get('GCS_JOB_DATA_BUCKET', f"{os.environ.get('GOOGLE_CLOUD_PROJECT', 'garak')}-job-data")
            
            # Verify buckets exist or create them
            self._ensure_bucket_exists(self.reports_bucket_name)
            self._ensure_bucket_exists(self.job_data_bucket_name)
            
            logger.info(f"GCS initialized - Reports: {self.reports_bucket_name}, Job Data: {self.job_data_bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize GCS: {e}")
            # Fallback to local storage
            self.use_gcs = False
            self._init_local()
    
    def _init_local(self):
        """Initialize local filesystem storage."""
        self.reports_dir = Path(os.environ.get('REPORT_DIR', 'reports'))
        self.job_data_dir = Path(os.environ.get('DATA_DIR', 'data'))
        
        # Create directories
        self.reports_dir.mkdir(exist_ok=True)
        self.job_data_dir.mkdir(exist_ok=True)
        
        logger.info(f"Local storage initialized - Reports: {self.reports_dir}, Job Data: {self.job_data_dir}")
    
    def _ensure_bucket_exists(self, bucket_name: str):
        """Ensure a GCS bucket exists, create if it doesn't."""
        try:
            bucket = self.gcs_client.bucket(bucket_name)
            bucket.reload()  # This will raise NotFound if bucket doesn't exist
        except NotFound:
            logger.warning(f"Bucket {bucket_name} not found - it may need to be created by Terraform")
        except Exception as e:
            logger.error(f"Error checking bucket {bucket_name}: {e}")
    
    # Job Data Methods
    
    def save_job_data(self, job_id: str, data: Dict[str, Any]) -> bool:
        """Save job data to storage."""
        try:
            filename = f"{job_id}.json"
            content = json.dumps(data, indent=2, default=str)
            
            if self.use_gcs:
                return self._save_to_gcs(self.job_data_bucket_name, filename, content, content_type='application/json')
            else:
                file_path = self.job_data_dir / filename
                with open(file_path, 'w') as f:
                    f.write(content)
                return True
                
        except Exception as e:
            logger.error(f"Error saving job data for {job_id}: {e}")
            return False
    
    def load_job_data(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Load job data from storage."""
        try:
            filename = f"{job_id}.json"
            
            if self.use_gcs:
                content = self._load_from_gcs(self.job_data_bucket_name, filename)
                if content:
                    return json.loads(content)
            else:
                file_path = self.job_data_dir / filename
                if file_path.exists():
                    with open(file_path, 'r') as f:
                        return json.load(f)
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading job data for {job_id}: {e}")
            return None
    
    def list_jobs(self) -> List[str]:
        """List all job IDs in storage."""
        try:
            if self.use_gcs:
                return self._list_gcs_files(self.job_data_bucket_name, suffix='.json')
            else:
                job_files = list(self.job_data_dir.glob('*.json'))
                return [f.stem for f in job_files]
                
        except Exception as e:
            logger.error(f"Error listing jobs: {e}")
            return []
    
    def delete_job_data(self, job_id: str) -> bool:
        """Delete job data from storage."""
        try:
            filename = f"{job_id}.json"
            
            if self.use_gcs:
                return self._delete_from_gcs(self.job_data_bucket_name, filename)
            else:
                file_path = self.job_data_dir / filename
                if file_path.exists():
                    file_path.unlink()
                return True
                
        except Exception as e:
            logger.error(f"Error deleting job data for {job_id}: {e}")
            return False
    
    # Report Methods
    
    def save_report(self, job_id: str, report_type: str, content: bytes, content_type: str = 'application/octet-stream') -> bool:
        """Save a report file to storage."""
        try:
            filename = f"{job_id}.{report_type}"
            
            if self.use_gcs:
                return self._save_to_gcs(self.reports_bucket_name, filename, content, content_type)
            else:
                file_path = self.reports_dir / filename
                with open(file_path, 'wb') as f:
                    f.write(content)
                return True
                
        except Exception as e:
            logger.error(f"Error saving report {report_type} for {job_id}: {e}")
            return False
    
    def load_report(self, job_id: str, report_type: str) -> Optional[bytes]:
        """Load a report file from storage."""
        try:
            filename = f"{job_id}.{report_type}"
            
            if self.use_gcs:
                content = self._load_from_gcs(self.reports_bucket_name, filename)
                return content.encode() if isinstance(content, str) else content
            else:
                file_path = self.reports_dir / filename
                if file_path.exists():
                    with open(file_path, 'rb') as f:
                        return f.read()
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading report {report_type} for {job_id}: {e}")
            return None
    
    def list_reports(self, job_id: str) -> List[str]:
        """List available report types for a job."""
        try:
            prefix = f"{job_id}."
            
            if self.use_gcs:
                files = self._list_gcs_files(self.reports_bucket_name, prefix=prefix)
                return [f.split('.', 1)[1] for f in files if '.' in f]
            else:
                report_files = list(self.reports_dir.glob(f"{job_id}.*"))
                return [f.suffix[1:] for f in report_files]  # Remove the dot
                
        except Exception as e:
            logger.error(f"Error listing reports for {job_id}: {e}")
            return []
    
    def delete_reports(self, job_id: str) -> bool:
        """Delete all reports for a job."""
        try:
            if self.use_gcs:
                # Delete all files with the job_id prefix
                bucket = self.gcs_client.bucket(self.reports_bucket_name)
                blobs = bucket.list_blobs(prefix=f"{job_id}.")
                for blob in blobs:
                    blob.delete()
                return True
            else:
                report_files = list(self.reports_dir.glob(f"{job_id}.*"))
                for file_path in report_files:
                    file_path.unlink()
                return True
                
        except Exception as e:
            logger.error(f"Error deleting reports for {job_id}: {e}")
            return False
    
    def get_report_url(self, job_id: str, report_type: str, expires_in: int = 3600) -> Optional[str]:
        """Get a signed URL for downloading a report (GCS only)."""
        if not self.use_gcs:
            return None
        
        try:
            filename = f"{job_id}.{report_type}"
            bucket = self.gcs_client.bucket(self.reports_bucket_name)
            blob = bucket.blob(filename)
            
            if not blob.exists():
                return None
            
            return blob.generate_signed_url(expiration=expires_in, method='GET')
            
        except Exception as e:
            logger.error(f"Error generating signed URL for {job_id}.{report_type}: {e}")
            return None
    
    # Private GCS Helper Methods
    
    def _save_to_gcs(self, bucket_name: str, filename: str, content: Any, content_type: str = 'application/octet-stream') -> bool:
        """Save content to GCS bucket."""
        try:
            bucket = self.gcs_client.bucket(bucket_name)
            blob = bucket.blob(filename)
            
            if isinstance(content, str):
                blob.upload_from_string(content, content_type=content_type)
            elif isinstance(content, bytes):
                blob.upload_from_string(content, content_type=content_type)
            else:
                # Assume it's a file-like object
                blob.upload_from_file(content, content_type=content_type)
            
            logger.debug(f"Saved {filename} to GCS bucket {bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving {filename} to GCS: {e}")
            return False
    
    def _load_from_gcs(self, bucket_name: str, filename: str) -> Optional[bytes]:
        """Load content from GCS bucket."""
        try:
            bucket = self.gcs_client.bucket(bucket_name)
            blob = bucket.blob(filename)
            
            if not blob.exists():
                return None
            
            return blob.download_as_bytes()
            
        except Exception as e:
            logger.error(f"Error loading {filename} from GCS: {e}")
            return None
    
    def _delete_from_gcs(self, bucket_name: str, filename: str) -> bool:
        """Delete file from GCS bucket."""
        try:
            bucket = self.gcs_client.bucket(bucket_name)
            blob = bucket.blob(filename)
            
            if blob.exists():
                blob.delete()
                logger.debug(f"Deleted {filename} from GCS bucket {bucket_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting {filename} from GCS: {e}")
            return False
    
    def _list_gcs_files(self, bucket_name: str, prefix: str = "", suffix: str = "") -> List[str]:
        """List files in GCS bucket with optional prefix and suffix filters."""
        try:
            bucket = self.gcs_client.bucket(bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)
            
            files = []
            for blob in blobs:
                if suffix and not blob.name.endswith(suffix):
                    continue
                
                # Remove prefix and suffix to get the base name
                name = blob.name
                if prefix:
                    name = name[len(prefix):]
                if suffix:
                    name = name[:-len(suffix)]
                
                files.append(name)
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing files in GCS bucket {bucket_name}: {e}")
            return []
    
    # Health Check Methods
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on storage backend."""
        if self.use_gcs:
            return self._gcs_health_check()
        else:
            return self._local_health_check()
    
    def _gcs_health_check(self) -> Dict[str, Any]:
        """Health check for GCS backend."""
        try:
            # Test connectivity by listing a small number of objects
            bucket = self.gcs_client.bucket(self.reports_bucket_name)
            list(bucket.list_blobs(max_results=1))
            
            return {
                'type': 'gcs',
                'status': 'healthy',
                'reports_bucket': self.reports_bucket_name,
                'job_data_bucket': self.job_data_bucket_name
            }
            
        except Exception as e:
            return {
                'type': 'gcs',
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def _local_health_check(self) -> Dict[str, Any]:
        """Health check for local filesystem backend."""
        try:
            # Test directory access
            reports_writable = os.access(self.reports_dir, os.W_OK)
            job_data_writable = os.access(self.job_data_dir, os.W_OK)
            
            if reports_writable and job_data_writable:
                status = 'healthy'
            else:
                status = 'unhealthy'
            
            return {
                'type': 'local',
                'status': status,
                'reports_dir': str(self.reports_dir),
                'job_data_dir': str(self.job_data_dir),
                'reports_writable': reports_writable,
                'job_data_writable': job_data_writable
            }
            
        except Exception as e:
            return {
                'type': 'local',
                'status': 'unhealthy',
                'error': str(e)
            }


# Global storage manager instance
storage_manager = StorageManager()


def get_storage_manager() -> StorageManager:
    """Get the global storage manager instance."""
    return storage_manager