"""
API Version 1 endpoints for Garak Dashboard.

This module contains all v1 API endpoints:
- scans.py: Scan management (create, list, get details, cancel)
- metadata.py: Discovery endpoints (generators, probes, models)  
- admin.py: Administrative endpoints (API key management, system stats)
"""

from .scans import api_v1
from .metadata import api_metadata
from .admin import api_admin

__all__ = ['api_v1', 'api_metadata', 'api_admin']