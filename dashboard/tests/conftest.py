"""
Pytest configuration and shared fixtures for Garak Dashboard tests.
"""

import os
import sys
import tempfile
import shutil
import sqlite3
from typing import Generator
import pytest
from flask import Flask
from flask.testing import FlaskClient

# Add dashboard directory to path for imports
dashboard_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, dashboard_dir)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up global test environment."""
    # Set environment variables for testing
    os.environ['DISABLE_AUTH'] = 'true'
    os.environ['FLASK_ENV'] = 'testing'


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp(prefix='garak_test_')
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)


@pytest.fixture
def test_database(temp_dir: str) -> str:
    """Create a test database with proper schema."""
    db_path = os.path.join(temp_dir, 'test_api_keys.db')
    
    # Create database with schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash TEXT UNIQUE NOT NULL,
            key_prefix TEXT NOT NULL,
            name TEXT,
            description TEXT,
            permissions TEXT DEFAULT 'read,write',
            rate_limit INTEGER DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            expires_at TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            usage_count INTEGER DEFAULT 0,
            user_id TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)')
    conn.commit()
    conn.close()
    
    # Set environment variable for the test database
    original_db_path = os.environ.get('API_KEYS_DB_PATH')
    os.environ['API_KEYS_DB_PATH'] = db_path
    
    yield db_path
    
    # Restore original database path
    if original_db_path:
        os.environ['API_KEYS_DB_PATH'] = original_db_path
    elif 'API_KEYS_DB_PATH' in os.environ:
        del os.environ['API_KEYS_DB_PATH']


@pytest.fixture
def app() -> Flask:
    """Create Flask app instance for testing."""
    from app import app
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def api_models():
    """Import and provide API models for testing."""
    from api.core.models import (
        ErrorResponse, CreateScanRequest, ScanStatus, ReportType,
        PermissionType, ScanProgressInfo, ScanMetadata, ScanResult,
        ReportInfo, ScanResponse, ScanListResponse, APIKeyInfo,
        APIKeyResponse, GeneratorInfo, ProbeInfo, ProbeCategory,
        RateLimitInfo, HealthResponse, UpdateScanRequest,
        CreateAPIKeyRequest
    )
    
    return {
        'ErrorResponse': ErrorResponse,
        'CreateScanRequest': CreateScanRequest,
        'ScanStatus': ScanStatus,
        'ReportType': ReportType,
        'PermissionType': PermissionType,
        'ScanProgressInfo': ScanProgressInfo,
        'ScanMetadata': ScanMetadata,
        'ScanResult': ScanResult,
        'ReportInfo': ReportInfo,
        'ScanResponse': ScanResponse,
        'ScanListResponse': ScanListResponse,
        'APIKeyInfo': APIKeyInfo,
        'APIKeyResponse': APIKeyResponse,
        'GeneratorInfo': GeneratorInfo,
        'ProbeInfo': ProbeInfo,
        'ProbeCategory': ProbeCategory,
        'RateLimitInfo': RateLimitInfo,
        'HealthResponse': HealthResponse,
        'UpdateScanRequest': UpdateScanRequest,
        'CreateAPIKeyRequest': CreateAPIKeyRequest,
    }


@pytest.fixture
def utils():
    """Provide utility functions for testing."""
    from api.core.utils import (
        get_generator_info, get_probe_category_info, get_generators,
        get_probe_categories, get_anthropic_models
    )
    
    return {
        'get_generator_info': get_generator_info,
        'get_probe_category_info': get_probe_category_info,
        'get_generators': get_generators,
        'get_probe_categories': get_probe_categories,
        'get_anthropic_models': get_anthropic_models,
    }


@pytest.fixture
def rate_limiter():
    """Provide rate limiter for testing."""
    from api.core.rate_limiter import RateLimiter
    return RateLimiter()


@pytest.fixture
def sample_scan_request():
    """Provide a sample scan request for testing."""
    return {
        'generator': 'huggingface',
        'model_name': 'gpt2',
        'probe_categories': ['dan'],
        'name': 'Test Scan',
        'description': 'A test scan for pytest',
        'api_keys': {}
    }


@pytest.fixture
def sample_api_key_request():
    """Provide a sample API key creation request for testing."""
    return {
        'name': 'Test API Key',
        'description': 'A test API key for pytest',
        'permissions': ['read', 'write'],
        'rate_limit': 100,
        'expires_days': 30
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "auth: authentication tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "models: Pydantic model tests")
    config.addinivalue_line("markers", "slow: slow running tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add default markers."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add markers based on test name patterns
        if "auth" in item.name.lower():
            item.add_marker(pytest.mark.auth)
        if "api" in item.name.lower() or "endpoint" in item.name.lower():
            item.add_marker(pytest.mark.api)
        if "model" in item.name.lower():
            item.add_marker(pytest.mark.models)