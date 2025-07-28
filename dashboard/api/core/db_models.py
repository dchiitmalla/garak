"""
SQLAlchemy database models for Garak Dashboard API.

This module defines the database schema using SQLAlchemy ORM,
supporting both SQLite and PostgreSQL backends.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Optional

from .database import Base


class APIKey(Base):
    """SQLAlchemy model for API keys."""
    
    __tablename__ = 'api_keys'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Key information
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    key_prefix = Column(String(16), nullable=False)
    
    # Metadata
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Permissions and limits
    permissions = Column(String(255), nullable=False, default='read,write')
    rate_limit = Column(Integer, nullable=False, default=100)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    usage_count = Column(Integer, nullable=False, default=0)
    
    # User association (for integration with Firebase Auth)
    user_id = Column(String(255), nullable=True, index=True)
    
    def __repr__(self):
        return f"<APIKey(id={self.id}, prefix='{self.key_prefix}', name='{self.name}')>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            'id': self.id,
            'key_prefix': self.key_prefix,
            'name': self.name,
            'description': self.description,
            'permissions': [p.strip() for p in self.permissions.split(',')],
            'rate_limit': self.rate_limit,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'user_id': self.user_id
        }
    
    def is_expired(self) -> bool:
        """Check if the API key has expired."""
        if self.expires_at is None:
            return False
        
        # Ensure we're comparing timezone-aware datetimes
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at
        
        # If expires_at is naive, assume it's UTC
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        return now > expires_at
    
    def has_permission(self, required_permission: str) -> bool:
        """Check if the API key has the required permission."""
        if not self.is_active:
            return False
        
        if self.is_expired():
            return False
        
        permissions = [p.strip() for p in self.permissions.split(',')]
        return required_permission in permissions or 'admin' in permissions
    
    def increment_usage(self):
        """Increment the usage count and update last used timestamp."""
        self.usage_count += 1
        self.last_used = datetime.now(timezone.utc)


class JobMetadata(Base):
    """SQLAlchemy model for job metadata (optional, for future use)."""
    
    __tablename__ = 'job_metadata'
    
    # Primary key
    id = Column(String(36), primary_key=True)  # UUID
    
    # Job information
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default='pending')
    
    # Configuration
    generator = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    probe_categories = Column(Text, nullable=True)  # JSON string
    probes = Column(Text, nullable=True)  # JSON string
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Progress tracking
    total_items = Column(Integer, nullable=True)
    completed_items = Column(Integer, nullable=True, default=0)
    
    # Association
    created_by_api_key_id = Column(Integer, nullable=True, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    
    # Storage paths
    output_file = Column(String(500), nullable=True)
    report_files = Column(Text, nullable=True)  # JSON string
    
    def __repr__(self):
        return f"<JobMetadata(id='{self.id}', status='{self.status}', model='{self.model_name}')>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'generator': self.generator,
            'model_name': self.model_name,
            'probe_categories': self.probe_categories,
            'probes': self.probes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'created_by_api_key_id': self.created_by_api_key_id,
            'user_id': self.user_id,
            'output_file': self.output_file,
            'report_files': self.report_files
        }


class UserSession(Base):
    """SQLAlchemy model for user sessions (optional, for future use)."""
    
    __tablename__ = 'user_sessions'
    
    # Primary key
    id = Column(String(36), primary_key=True)  # UUID
    
    # User information
    user_id = Column(String(255), nullable=False, index=True)
    firebase_uid = Column(String(255), nullable=True, index=True)
    
    # Session data
    session_data = Column(Text, nullable=True)  # JSON string
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    last_activity = Column(DateTime(timezone=True), nullable=False, default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    def __repr__(self):
        return f"<UserSession(id='{self.id}', user_id='{self.user_id}')>"
    
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at