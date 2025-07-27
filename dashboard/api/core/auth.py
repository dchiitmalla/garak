"""
API key authentication system for Garak Dashboard public API.

This module provides:
- API key generation and validation
- SQLite database storage for API keys
- Authentication decorator for public API endpoints
"""

import os
import secrets
import hashlib
import sqlite3
import functools
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from flask import request, jsonify, current_app, g


class APIKeyManager:
    """Manages API key generation, storage, and validation."""
    
    def __init__(self, db_path: str = None):
        """Initialize the API key manager with database path."""
        if db_path is None:
            # Use dashboard data directory
            data_dir = os.environ.get('DATA_DIR', 
                                    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, 'api_keys.db')
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database with API keys table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
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
                    usage_count INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
    
    def generate_api_key(self, name: str = None, description: str = None, 
                        permissions: str = 'read,write', rate_limit: int = 100,
                        expires_days: int = None) -> tuple[str, Dict[str, Any]]:
        """
        Generate a new API key.
        
        Args:
            name: Human-readable name for the key
            description: Description of the key's purpose
            permissions: Comma-separated permissions (read,write,admin)
            rate_limit: Requests per minute limit
            expires_days: Number of days until key expires (None for no expiration)
            
        Returns:
            tuple: (api_key, key_metadata)
        """
        # Generate a secure random API key
        api_key = f"garak_{secrets.token_urlsafe(32)}"
        
        # Create hash for storage (we never store the actual key)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_prefix = api_key[:12] + "..."  # For display purposes
        
        # Calculate expiration if specified
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO api_keys 
                (key_hash, key_prefix, name, description, permissions, rate_limit, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (key_hash, key_prefix, name, description, permissions, rate_limit, expires_at))
            
            key_id = cursor.lastrowid
            conn.commit()
        
        # Return the API key and metadata
        metadata = {
            'id': key_id,
            'key_prefix': key_prefix,
            'name': name,
            'description': description,
            'permissions': permissions.split(','),
            'rate_limit': rate_limit,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'created_at': datetime.now().isoformat()
        }
        
        return api_key, metadata
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key and return its metadata.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Dictionary with key metadata if valid, None if invalid
        """
        if not api_key or not api_key.startswith('garak_'):
            return None
        
        # Hash the provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM api_keys 
                WHERE key_hash = ? AND is_active = 1
            ''', (key_hash,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Check if key has expired
            if row['expires_at']:
                expires_at = datetime.fromisoformat(row['expires_at'])
                if datetime.now() > expires_at:
                    return None
            
            # Update last used timestamp and usage count
            conn.execute('''
                UPDATE api_keys 
                SET last_used = CURRENT_TIMESTAMP, usage_count = usage_count + 1
                WHERE id = ?
            ''', (row['id'],))
            conn.commit()
            
            # Return key metadata
            return {
                'id': row['id'],
                'key_prefix': row['key_prefix'],
                'name': row['name'],
                'description': row['description'],
                'permissions': row['permissions'].split(',') if row['permissions'] else [],
                'rate_limit': row['rate_limit'],
                'usage_count': row['usage_count'] + 1,
                'last_used': datetime.now().isoformat(),
                'created_at': row['created_at'],
                'expires_at': row['expires_at']
            }
    
    def list_api_keys(self) -> list[Dict[str, Any]]:
        """List all API keys (without the actual key values)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT id, key_prefix, name, description, permissions, rate_limit,
                       created_at, last_used, expires_at, is_active, usage_count
                FROM api_keys 
                ORDER BY created_at DESC
            ''')
            
            keys = []
            for row in cursor.fetchall():
                keys.append({
                    'id': row['id'],
                    'key_prefix': row['key_prefix'],
                    'name': row['name'],
                    'description': row['description'],
                    'permissions': row['permissions'].split(',') if row['permissions'] else [],
                    'rate_limit': row['rate_limit'],
                    'created_at': row['created_at'],
                    'last_used': row['last_used'],
                    'expires_at': row['expires_at'],
                    'is_active': bool(row['is_active']),
                    'usage_count': row['usage_count']
                })
            
            return keys
    
    def revoke_api_key(self, key_id: int) -> bool:
        """Revoke an API key by setting is_active to False."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                UPDATE api_keys SET is_active = 0 WHERE id = ?
            ''', (key_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_api_key(self, key_id: int) -> bool:
        """Permanently delete an API key."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                DELETE FROM api_keys WHERE id = ?
            ''', (key_id,))
            conn.commit()
            return cursor.rowcount > 0


# Global API key manager instance
api_key_manager = APIKeyManager()


def get_api_key_from_request() -> Optional[str]:
    """Extract API key from request headers."""
    # Check Authorization header: "Bearer garak_..."
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header.split('Bearer ')[1].strip()
    
    # Check X-API-Key header
    api_key = request.headers.get('X-API-Key', '').strip()
    if api_key:
        return api_key
    
    # Check query parameter (less secure, but sometimes necessary)
    api_key = request.args.get('api_key', '').strip()
    if api_key:
        return api_key
    
    return None


def api_key_required(permissions: list = None):
    """
    Decorator to require a valid API key for public API endpoints.
    
    Args:
        permissions: List of required permissions (e.g., ['read'], ['write'], ['admin'])
    """
    if permissions is None:
        permissions = ['read']
    
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped_view(*args, **kwargs):
            # Get API key from request
            api_key = get_api_key_from_request()
            
            if not api_key:
                return jsonify({
                    'error': 'API key required',
                    'message': 'Provide API key in Authorization header (Bearer token) or X-API-Key header'
                }), 401
            
            # Validate API key
            key_info = api_key_manager.validate_api_key(api_key)
            if not key_info:
                return jsonify({
                    'error': 'Invalid API key',
                    'message': 'The provided API key is invalid or expired'
                }), 401
            
            # Check permissions
            key_permissions = key_info.get('permissions', [])
            if not any(perm in key_permissions for perm in permissions):
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'API key requires one of these permissions: {permissions}',
                    'key_permissions': key_permissions
                }), 403
            
            # Store key info in Flask's g object for use in the view
            g.api_key_info = key_info
            
            # Log API usage
            current_app.logger.info(
                f"API request: {request.method} {request.path} - "
                f"Key: {key_info['key_prefix']} ({key_info['name']})"
            )
            
            return view_func(*args, **kwargs)
        
        return wrapped_view
    return decorator


def admin_required(view_func):
    """Decorator that requires admin permissions."""
    return api_key_required(permissions=['admin'])(view_func)


def write_required(view_func):
    """Decorator that requires write permissions."""
    return api_key_required(permissions=['write', 'admin'])(view_func)


def read_required(view_func):
    """Decorator that requires read permissions."""
    return api_key_required(permissions=['read', 'write', 'admin'])(view_func)