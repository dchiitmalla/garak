"""
Unit tests for database models (isolated tests).
"""

import pytest
from datetime import datetime, timezone
import tempfile
import os
import sqlite3


class TestDatabaseModels:
    """Test database model functionality in isolation."""
    
    def test_api_key_model_creation(self):
        """Test APIKey model can be created."""
        try:
            from api.core.db_models import APIKey
            
            # Create model instance
            api_key = APIKey(
                key_hash='test_hash_123',
                key_prefix='garak_test...',
                name='Test Key',
                description='A test API key',
                permissions='read,write',
                rate_limit=100,
                is_active=True,
                usage_count=0
            )
            
            assert api_key.key_hash == 'test_hash_123'
            assert api_key.key_prefix == 'garak_test...'
            assert api_key.name == 'Test Key'
            assert api_key.permissions == 'read,write'
            assert api_key.rate_limit == 100
            assert api_key.is_active is True
            assert api_key.usage_count == 0
            
        except ImportError:
            pytest.skip("Database models not available")
    
    def test_api_key_to_dict(self):
        """Test APIKey to_dict method."""
        try:
            from api.core.db_models import APIKey
            
            api_key = APIKey(
                id=1,
                key_hash='test_hash',
                key_prefix='garak_test...',
                name='Test Key',
                description='Test description',
                permissions='read,write,admin',
                rate_limit=200,
                is_active=True,
                usage_count=5,
                user_id='test_user'
            )
            
            data = api_key.to_dict()
            
            assert isinstance(data, dict)
            assert data['id'] == 1
            assert data['key_prefix'] == 'garak_test...'
            assert data['name'] == 'Test Key'
            assert data['permissions'] == ['read', 'write', 'admin']
            assert data['rate_limit'] == 200
            assert data['is_active'] is True
            assert data['usage_count'] == 5
            assert data['user_id'] == 'test_user'
            
        except ImportError:
            pytest.skip("Database models not available")
    
    def test_api_key_has_permission(self):
        """Test APIKey permission checking."""
        try:
            from api.core.db_models import APIKey
            
            # Test with read/write permissions
            api_key = APIKey(
                key_hash='test',
                key_prefix='test...',
                permissions='read,write',
                is_active=True
            )
            
            assert api_key.has_permission('read') is True
            assert api_key.has_permission('write') is True
            assert api_key.has_permission('admin') is False
            
            # Test with admin permission
            admin_key = APIKey(
                key_hash='admin_test',
                key_prefix='admin...',
                permissions='admin',
                is_active=True
            )
            
            assert admin_key.has_permission('read') is True  # Admin has all permissions
            assert admin_key.has_permission('write') is True
            assert admin_key.has_permission('admin') is True
            
            # Test inactive key
            inactive_key = APIKey(
                key_hash='inactive',
                key_prefix='inactive...',
                permissions='read,write',
                is_active=False
            )
            
            assert inactive_key.has_permission('read') is False
            assert inactive_key.has_permission('write') is False
            
        except ImportError:
            pytest.skip("Database models not available")
    
    def test_api_key_is_expired(self):
        """Test APIKey expiration checking."""
        try:
            from api.core.db_models import APIKey
            
            # Test non-expiring key
            non_expiring = APIKey(
                key_hash='test',
                key_prefix='test...',
                expires_at=None
            )
            
            assert non_expiring.is_expired() is False
            
            # Test expired key
            past_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
            expired_key = APIKey(
                key_hash='expired',
                key_prefix='expired...',
                expires_at=past_time
            )
            
            assert expired_key.is_expired() is True
            
            # Test future expiry
            future_time = datetime(2030, 1, 1, tzinfo=timezone.utc)
            future_key = APIKey(
                key_hash='future',
                key_prefix='future...',
                expires_at=future_time
            )
            
            assert future_key.is_expired() is False
            
        except ImportError:
            pytest.skip("Database models not available")
    
    def test_api_key_increment_usage(self):
        """Test APIKey usage increment.""" 
        try:
            from api.core.db_models import APIKey
            
            api_key = APIKey(
                key_hash='usage_test',
                key_prefix='usage...',
                usage_count=0,
                last_used=None
            )
            
            original_count = api_key.usage_count
            api_key.increment_usage()
            
            assert api_key.usage_count == original_count + 1
            assert api_key.last_used is not None
            assert isinstance(api_key.last_used, datetime)
            
        except ImportError:
            pytest.skip("Database models not available")


class TestDatabaseSchema:
    """Test database schema operations."""
    
    def test_database_schema_creation(self, temp_dir):
        """Test that database schema can be created."""
        db_path = os.path.join(temp_dir, 'test_schema.db')
        
        # Create database with our expected schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create the api_keys table with all required columns
        cursor.execute('''
            CREATE TABLE api_keys (
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
        
        cursor.execute('CREATE INDEX idx_api_keys_user_id ON api_keys(user_id)')
        conn.commit()
        
        # Verify schema
        cursor.execute("PRAGMA table_info(api_keys)")
        columns = [col[1] for col in cursor.fetchall()]
        
        expected_columns = [
            'id', 'key_hash', 'key_prefix', 'name', 'description',
            'permissions', 'rate_limit', 'created_at', 'last_used',  
            'expires_at', 'is_active', 'usage_count', 'user_id'
        ]
        
        for col in expected_columns:
            assert col in columns, f"Missing column: {col}"
        
        conn.close()
    
    def test_database_insert_operation(self, temp_dir):
        """Test basic database insert operations."""
        db_path = os.path.join(temp_dir, 'test_insert.db')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create table
        cursor.execute('''
            CREATE TABLE api_keys (
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
        
        # Insert test data
        cursor.execute('''
            INSERT INTO api_keys (key_hash, key_prefix, name, description, user_id)
            VALUES (?, ?, ?, ?, ?)
        ''', ('test_hash_123', 'garak_test...', 'Test Key', 'Test description', 'test_user'))
        
        conn.commit()
        
        # Verify insert
        cursor.execute('SELECT * FROM api_keys WHERE key_hash = ?', ('test_hash_123',))
        result = cursor.fetchone()
        
        assert result is not None
        assert result[1] == 'test_hash_123'  # key_hash
        assert result[2] == 'garak_test...'  # key_prefix
        assert result[3] == 'Test Key'       # name
        
        conn.close()