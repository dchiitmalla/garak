"""
Pydantic models for Garak Dashboard API request/response validation.

This module defines the data models used for API request validation
and response serialization in the public API.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, validator


class ScanStatus(str, Enum):
    """Possible scan statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReportType(str, Enum):
    """Available report types."""
    JSON = "json"
    JSONL = "jsonl"
    HTML = "html"
    HITS = "hits"


class PermissionType(str, Enum):
    """API key permission types."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


# Request Models

class CreateScanRequest(BaseModel):
    """Request model for creating a new garak scan."""
    
    generator: str = Field(..., description="Model generator type (e.g., 'openai', 'huggingface')")
    model_name: str = Field(..., description="Specific model name to test")
    probe_categories: List[str] = Field(
        default=[], 
        description="List of probe categories to run (e.g., ['dan', 'security'])"
    )
    probes: Optional[List[str]] = Field(
        default=None,
        description="Specific probes to run (overrides categories)"
    )
    api_keys: Dict[str, str] = Field(
        default_factory=dict,
        description="API keys for model access (will be masked in responses)"
    )
    parallel_attempts: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of parallel attempts per probe"
    )
    name: Optional[str] = Field(
        default=None,
        description="Human-readable name for the scan"
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the scan purpose"
    )
    rest_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="REST endpoint configuration (for REST generator only)"
    )
    
    @validator('probe_categories')
    def validate_probe_categories(cls, v):
        """Validate probe categories."""
        valid_categories = [
            'dan', 'security', 'privacy', 'toxicity', 'hallucination',
            'performance', 'robustness', 'ethics', 'stereotype'
        ]
        for category in v:
            if category not in valid_categories:
                raise ValueError(f"Invalid probe category: {category}. Valid options: {valid_categories}")
        return v
    
    @validator('generator')
    def validate_generator(cls, v):
        """Validate generator type."""
        valid_generators = [
            'openai', 'huggingface', 'cohere', 'anthropic', 'ollama',
            'replicate', 'vertexai', 'llamacpp', 'mistral', 'litellm',
            'rest',  # REST endpoint generator
            'test.Blank', 'test.Repeat'  # Test generators for development
        ]
        if v not in valid_generators:
            raise ValueError(f"Invalid generator: {v}. Valid options: {valid_generators}")
        return v


class UpdateScanRequest(BaseModel):
    """Request model for updating scan metadata."""
    
    name: Optional[str] = Field(default=None, description="Update scan name")
    description: Optional[str] = Field(default=None, description="Update scan description")


class CreateAPIKeyRequest(BaseModel):
    """Request model for creating a new API key."""
    
    name: str = Field(..., description="Human-readable name for the API key")
    description: Optional[str] = Field(default=None, description="Description of the key's purpose")
    permissions: List[PermissionType] = Field(
        default=[PermissionType.READ, PermissionType.WRITE],
        description="List of permissions for the API key"
    )
    rate_limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Requests per minute limit"
    )
    expires_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=365,
        description="Number of days until key expires (None for no expiration)"
    )


# Response Models

class ScanProgressInfo(BaseModel):
    """Progress information for a running scan."""
    
    completed_items: int = Field(..., description="Number of completed test items")
    total_items: Optional[int] = Field(default=None, description="Total number of test items")
    progress_percent: float = Field(..., ge=0, le=100, description="Progress percentage")
    elapsed_time: str = Field(..., description="Time elapsed since scan start")
    estimated_remaining: Optional[str] = Field(default=None, description="Estimated time remaining")
    estimated_completion: Optional[str] = Field(default=None, description="Estimated completion time")


class ScanMetadata(BaseModel):
    """Metadata for a scan."""
    
    scan_id: str = Field(..., description="Unique scan identifier")
    name: Optional[str] = Field(default=None, description="Human-readable scan name")
    description: Optional[str] = Field(default=None, description="Scan description")
    generator: str = Field(..., description="Model generator used")
    model_name: str = Field(..., description="Model name tested")
    probe_categories: List[str] = Field(..., description="Probe categories run")
    probes: List[str] = Field(..., description="Specific probes executed")
    status: ScanStatus = Field(..., description="Current scan status")
    created_at: datetime = Field(..., description="Scan creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Scan start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Scan completion timestamp")
    duration_seconds: Optional[float] = Field(default=None, description="Total scan duration")
    parallel_attempts: int = Field(..., description="Number of parallel attempts")
    progress: Optional[ScanProgressInfo] = Field(default=None, description="Progress information")


class ScanResult(BaseModel):
    """Summary results from a completed scan."""
    
    total_probes: int = Field(..., description="Total number of probes run")
    total_attempts: int = Field(..., description="Total number of test attempts")
    failed_attempts: int = Field(..., description="Number of failed attempts")
    success_rate: float = Field(..., ge=0, le=100, description="Overall success rate percentage")
    trust_scores: Dict[str, Any] = Field(default_factory=dict, description="Trust scores by category")
    key_findings: List[str] = Field(default_factory=list, description="Key security findings")


class ReportInfo(BaseModel):
    """Information about available reports."""
    
    type: ReportType = Field(..., description="Report type")
    file_path: str = Field(..., description="File path to the report")
    file_size: int = Field(..., description="File size in bytes")
    created_at: datetime = Field(..., description="Report creation timestamp")
    download_url: str = Field(..., description="URL to download the report")


class ScanResponse(BaseModel):
    """Complete scan information response."""
    
    metadata: ScanMetadata = Field(..., description="Scan metadata")
    results: Optional[ScanResult] = Field(default=None, description="Scan results (if completed)")
    reports: List[ReportInfo] = Field(default_factory=list, description="Available reports")
    output_log: Optional[str] = Field(default=None, description="Scan output log")


class ScanListResponse(BaseModel):
    """Response for listing scans."""
    
    scans: List[ScanMetadata] = Field(..., description="List of scans")
    total: int = Field(..., description="Total number of scans")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")


class APIKeyInfo(BaseModel):
    """API key information (without the actual key)."""
    
    id: int = Field(..., description="Unique key identifier")
    key_prefix: str = Field(..., description="First few characters of the key")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(default=None, description="Key description")
    permissions: List[PermissionType] = Field(..., description="Key permissions")
    rate_limit: int = Field(..., description="Requests per minute limit")
    usage_count: int = Field(..., description="Total number of requests made")
    created_at: datetime = Field(..., description="Key creation timestamp")
    last_used: Optional[datetime] = Field(default=None, description="Last usage timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="Key expiration timestamp")
    is_active: bool = Field(..., description="Whether the key is active")


class APIKeyResponse(BaseModel):
    """Response when creating a new API key."""
    
    api_key: str = Field(..., description="The generated API key (only shown once)")
    key_info: APIKeyInfo = Field(..., description="Key metadata")


class GeneratorInfo(BaseModel):
    """Information about a model generator."""
    
    name: str = Field(..., description="Generator identifier")
    display_name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(default=None, description="Generator description")
    requires_api_key: bool = Field(..., description="Whether an API key is required")
    supported_models: List[str] = Field(default_factory=list, description="List of supported models")


class ProbeInfo(BaseModel):
    """Information about a security probe."""
    
    name: str = Field(..., description="Probe identifier")
    display_name: str = Field(..., description="Human-readable name")
    category: str = Field(..., description="Probe category")
    description: Optional[str] = Field(default=None, description="Probe description")
    recommended_detectors: List[str] = Field(default_factory=list, description="Recommended detectors")


class ProbeCategory(BaseModel):
    """Information about a probe category."""
    
    name: str = Field(..., description="Category name")
    display_name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(default=None, description="Category description")
    probes: List[ProbeInfo] = Field(..., description="Probes in this category")


class ErrorResponse(BaseModel):
    """Standard error response format."""
    
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = Field(default=None, description="Additional error details")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Error timestamp")


class RateLimitInfo(BaseModel):
    """Rate limiting information."""
    
    requests: int = Field(..., description="Current request count in window")
    limit: int = Field(..., description="Maximum requests allowed")
    remaining: int = Field(..., description="Remaining requests in window")
    window: int = Field(..., description="Time window in seconds")
    reset_time: Optional[int] = Field(default=None, description="Unix timestamp when limit resets")


class HealthResponse(BaseModel):
    """API health check response."""
    
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="API version")
    services: Dict[str, str] = Field(default_factory=dict, description="Service status")


# Utility functions for model conversion

def scan_to_metadata(job_data: Dict[str, Any]) -> ScanMetadata:
    """Convert internal job data to ScanMetadata model."""
    
    def _parse_datetime(dt_value):
        """Parse datetime value that could be string or datetime object."""
        if dt_value is None:
            # Return current time if no timestamp available
            return datetime.now(timezone.utc)
        
        if isinstance(dt_value, str):
            parsed = datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
        elif isinstance(dt_value, datetime):
            parsed = dt_value
        else:
            # Try to parse as string anyway
            try:
                parsed = datetime.fromisoformat(str(dt_value).replace('Z', '+00:00'))
            except (ValueError, TypeError):
                # If all else fails, return current time
                return datetime.now(timezone.utc)
        
        # Ensure the datetime is timezone-aware
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        
        return parsed
    
    return ScanMetadata(
        scan_id=job_data.get('id', job_data.get('job_id')),
        name=job_data.get('name'),
        description=job_data.get('description'),
        generator=job_data.get('generator', ''),
        model_name=job_data.get('model_name', ''),
        probe_categories=job_data.get('probe_categories', []),
        probes=job_data.get('probes', []),
        status=ScanStatus(job_data.get('status', 'pending')),
        created_at=_parse_datetime(job_data.get('created_at')),
        started_at=_parse_datetime(job_data.get('start_time')),
        completed_at=_parse_datetime(job_data.get('end_time')),
        duration_seconds=job_data.get('duration'),
        parallel_attempts=job_data.get('parallel_attempts', 1),
        progress=_convert_progress_info(job_data.get('progress'))
    )


def _convert_progress_info(progress_data: Optional[Dict[str, Any]]) -> Optional[ScanProgressInfo]:
    """Convert internal progress data to ScanProgressInfo model."""
    if not progress_data:
        return None
    
    return ScanProgressInfo(
        completed_items=progress_data.get('completed', 0),
        total_items=progress_data.get('total'),
        progress_percent=progress_data.get('percent', 0),
        elapsed_time=progress_data.get('elapsed_seconds', '0s'),
        estimated_remaining=progress_data.get('remaining_seconds'),
        estimated_completion=progress_data.get('estimated_completion')
    )