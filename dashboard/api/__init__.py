"""
Garak Dashboard Public API Package.

This package provides a public REST API for the Garak LLM vulnerability scanner,
allowing programmatic access to security scanning capabilities.

Package Structure:
- core/: Core functionality (auth, models, rate limiting, utilities)
- v1/: API version 1 endpoints (scans, metadata, admin)
- docs.py: OpenAPI documentation and Swagger UI
"""

from flask import Blueprint

# Import all blueprints for easy registration
from .v1.scans import api_v1
from .v1.metadata import api_metadata  
from .v1.admin import api_admin
from .docs import api_docs, create_swagger_blueprint

__all__ = ['api_v1', 'api_metadata', 'api_admin', 'api_docs', 'create_swagger_blueprint']

__version__ = '1.0.0'