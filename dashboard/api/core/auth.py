"""
API key authentication system for Garak Dashboard public API.

This module provides:
- API key generation and validation
- Database storage for API keys (SQLite/PostgreSQL)
- Authentication decorator for public API endpoints
"""

import os
import secrets
import hashlib
import functools
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from flask import request, jsonify, current_app, g
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .database import db_manager, get_database_session
from .db_models import APIKey


class APIKeyManager:
    """Manages API key generation, storage, and validation using SQLAlchemy."""
    
    def __init__(self):
        """Initialize the API key manager."""
        self.logger = logging.getLogger(__name__)
        # Ensure database tables are created
        db_manager.create_tables()
    
    def _get_session(self) -> Session:
        """Get a database session."""
        return db_manager.get_session()
    
    def generate_api_key(self, name: str = None, description: str = None, 
                        permissions: str = 'read,write', rate_limit: int = 100,
                        expires_days: int = None, user_id: str = None) -> tuple[str, Dict[str, Any]]:
        """Generate a new API key and store it in the database."""
        try:
            # Generate a secure API key
            api_key = f"garak_{secrets.token_urlsafe(32)}"
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            key_prefix = api_key[:8] + '...'  # For identification purposes
            
            # Calculate expiration date
            expires_at = None
            if expires_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_days)
            
            # Create API key record
            with self._get_session() as session:
                api_key_record = APIKey(
                    key_hash=key_hash,
                    key_prefix=key_prefix,
                    name=name,
                    description=description,
                    permissions=permissions,
                    rate_limit=rate_limit,
                    expires_at=expires_at,
                    user_id=user_id
                )
                
                session.add(api_key_record)
                session.commit()
                session.refresh(api_key_record)
                
                metadata = api_key_record.to_dict()
            
            self.logger.info(f"Generated API key with ID {metadata['id']} for user {user_id or 'unknown'}")
            return api_key, metadata
            
        except IntegrityError as e:
            self.logger.error(f"API key generation failed - duplicate key: {e}")
            raise ValueError("API key generation failed - please try again")
        except SQLAlchemyError as e:
            self.logger.error(f"Database error during API key generation: {e}")
            raise RuntimeError("Database error during API key generation")
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key and return its metadata if valid."""
        if not api_key or not api_key.startswith('garak_'):
            return None
        
        try:
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            with self._get_session() as session:
                api_key_record = session.query(APIKey).filter(
                    APIKey.key_hash == key_hash,
                    APIKey.is_active == True
                ).first()
                
                if not api_key_record:
                    return None
                
                # Check if expired
                if api_key_record.is_expired():
                    self.logger.warning(f"Expired API key used: {api_key_record.key_prefix}")
                    return None
                
                # Update usage statistics
                api_key_record.increment_usage()
                session.commit()
                
                return api_key_record.to_dict()
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error during API key validation: {e}")
            return None
    
    def list_api_keys(self, user_id: str = None) -> List[Dict[str, Any]]:
        """List API keys (without revealing the actual keys)."""
        try:
            with self._get_session() as session:
                query = session.query(APIKey)
                
                # Filter by user if specified
                if user_id:
                    query = query.filter(APIKey.user_id == user_id)
                
                api_keys = query.order_by(APIKey.created_at.desc()).all()
                return [key.to_dict() for key in api_keys]
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error during API key listing: {e}")
            return []
    
    def revoke_api_key(self, key_id: int, user_id: str = None) -> bool:
        """Revoke (deactivate) an API key."""
        try:
            with self._get_session() as session:
                query = session.query(APIKey).filter(APIKey.id == key_id)
                
                # If user_id provided, ensure they own this key
                if user_id:
                    query = query.filter(APIKey.user_id == user_id)
                
                api_key_record = query.first()
                if not api_key_record:
                    return False
                
                api_key_record.is_active = False
                session.commit()
                
                self.logger.info(f"Revoked API key {key_id} for user {user_id or 'admin'}")
                return True
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error during API key revocation: {e}")
            return False
    
    def delete_api_key(self, key_id: int, user_id: str = None) -> bool:
        """Permanently delete an API key."""
        try:
            with self._get_session() as session:
                query = session.query(APIKey).filter(APIKey.id == key_id)
                
                # If user_id provided, ensure they own this key
                if user_id:
                    query = query.filter(APIKey.user_id == user_id)
                
                api_key_record = query.first()
                if not api_key_record:
                    return False
                
                session.delete(api_key_record)
                session.commit()
                
                self.logger.info(f"Deleted API key {key_id} for user {user_id or 'admin'}")
                return True
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error during API key deletion: {e}")
            return False
    
    def get_api_key(self, key_id: int, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get API key details by ID."""
        try:
            with self._get_session() as session:
                query = session.query(APIKey).filter(APIKey.id == key_id)
                
                # If user_id provided, ensure they own this key
                if user_id:
                    query = query.filter(APIKey.user_id == user_id)
                
                api_key_record = query.first()
                if not api_key_record:
                    return None
                
                return api_key_record.to_dict()
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error during API key retrieval: {e}")
            return None
    
    def update_api_key(self, key_id: int, updates: Dict[str, Any], user_id: str = None) -> bool:
        """Update API key metadata."""
        try:
            with self._get_session() as session:
                query = session.query(APIKey).filter(APIKey.id == key_id)
                
                # If user_id provided, ensure they own this key
                if user_id:
                    query = query.filter(APIKey.user_id == user_id)
                
                api_key_record = query.first()
                if not api_key_record:
                    return False
                
                # Update allowed fields
                allowed_fields = ['name', 'description', 'permissions', 'rate_limit', 'expires_at']
                for field, value in updates.items():
                    if field in allowed_fields and hasattr(api_key_record, field):
                        setattr(api_key_record, field, value)
                
                session.commit()
                self.logger.info(f"Updated API key {key_id} for user {user_id or 'admin'}")
                return True
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error during API key update: {e}")
            return False


# Global API key manager instance
api_key_manager = APIKeyManager()


def extract_api_key(request) -> Optional[str]:
    """Extract API key from request headers or query parameters."""
    # Try Authorization header (Bearer token)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Try X-API-Key header
    api_key = request.headers.get('X-API-Key')
    if api_key:
        return api_key
    
    # Try query parameter (less secure, but supported)
    api_key = request.args.get('api_key')
    if api_key:
        return api_key
    
    return None


def api_key_required(f):
    """Decorator that requires a valid API key for endpoint access."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip API key authentication if disabled
        if os.environ.get("DISABLE_AUTH", "").lower() == "true":
            # Create a mock API key info for bypass mode
            g.api_key_info = {
                'id': 'bypass',
                'name': 'Auth Disabled',
                'permissions': ['read', 'write', 'admin'],
                'rate_limit': 999999,
                'user_id': 'bypass_user',
                'key_prefix': 'bypass_...'
            }
            return f(*args, **kwargs)
        
        api_key = extract_api_key(request)
        
        if not api_key:
            return jsonify({
                'error': 'API key required',
                'message': 'Provide API key in Authorization header (Bearer token) or X-API-Key header'
            }), 401
        
        # Validate the API key
        key_info = api_key_manager.validate_api_key(api_key)
        if not key_info:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is invalid, expired, or inactive'
            }), 401
        
        # Store key info in Flask's g object for use in the endpoint
        g.api_key_info = key_info
        
        return f(*args, **kwargs)
    
    return decorated_function


def permission_required(required_permission: str):
    """Decorator that requires a specific permission level."""
    def decorator(f):
        @functools.wraps(f)
        @api_key_required
        def decorated_function(*args, **kwargs):
            key_info = g.api_key_info
            
            # Check if the API key has the required permission
            permissions = key_info['permissions'] if isinstance(key_info['permissions'], list) else [p.strip() for p in key_info['permissions'].split(',')]
            
            if required_permission not in permissions and 'admin' not in permissions:
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'This endpoint requires {required_permission} permission'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


# Convenience decorators for common permission levels
def read_required(f):
    """Decorator that requires read permission."""
    return permission_required('read')(f)


def write_required(f):
    """Decorator that requires write permission."""
    return permission_required('write')(f)


def admin_required(f):
    """Decorator that requires admin permission."""
    return permission_required('admin')(f)


def get_current_user_id() -> Optional[str]:
    """Get the current user ID from the API key context."""
    if hasattr(g, 'api_key_info') and g.api_key_info:
        return g.api_key_info.get('user_id')
    return None


def is_admin_user() -> bool:
    """Check if the current user has admin permissions."""
    if not hasattr(g, 'api_key_info') or not g.api_key_info:
        return False
    
    permissions = g.api_key_info['permissions'] if isinstance(g.api_key_info['permissions'], list) else [p.strip() for p in g.api_key_info['permissions'].split(',')]
    return 'admin' in permissions