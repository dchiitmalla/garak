"""
Core API functionality for Garak Dashboard.

This module contains shared components used across the API:
- Authentication and authorization
- Pydantic models for request/response validation
- Rate limiting with Redis
- Shared utilities and helper functions
"""

from .auth import api_key_manager, api_key_required, read_required, write_required, admin_required
from .models import *  # Import all Pydantic models
from .rate_limiter import rate_limiter, rate_limit, get_rate_limit_status
from .utils import (
    get_jobs_data, get_probe_categories, get_generators, get_anthropic_models,
    run_garak_job_wrapper, validate_json_request, create_error_handler,
    get_generator_info, get_probe_category_info
)

__all__ = [
    # Auth
    'api_key_manager', 'api_key_required', 'read_required', 'write_required', 'admin_required',
    # Rate limiting
    'rate_limiter', 'rate_limit', 'get_rate_limit_status',
    # Utilities
    'get_jobs_data', 'get_probe_categories', 'get_generators', 'get_anthropic_models',
    'run_garak_job_wrapper', 'validate_json_request', 'create_error_handler',
    'get_generator_info', 'get_probe_category_info'
]