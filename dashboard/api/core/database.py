"""
Database configuration and connection management for Garak Dashboard API.

This module provides database abstraction supporting both SQLite (development) 
and PostgreSQL (production) backends.
"""

import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
import urllib.parse

logger = logging.getLogger(__name__)

# SQLAlchemy base for models
Base = declarative_base()

class DatabaseManager:
    """Manages database connections and provides session management."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database manager with connection URL."""
        self.database_url = database_url or self._get_database_url()
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _get_database_url(self) -> str:
        """Get database URL from environment variables."""
        # Check for explicit database URL first
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            return database_url
        
        # Check for Google Cloud SQL connection
        if os.environ.get('GOOGLE_CLOUD_PROJECT'):
            return self._build_cloud_sql_url()
        
        # Default to SQLite for development
        return self._build_sqlite_url()
    
    def _build_cloud_sql_url(self) -> str:
        """Build PostgreSQL URL for Google Cloud SQL."""
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        region = os.environ.get('CLOUD_SQL_REGION', 'us-central1')
        instance_name = os.environ.get('CLOUD_SQL_INSTANCE', 'garak-dashboard-db')
        database_name = os.environ.get('CLOUD_SQL_DATABASE', 'garak_dashboard')
        username = os.environ.get('CLOUD_SQL_USERNAME', 'garak_user')
        password = os.environ.get('CLOUD_SQL_PASSWORD', '')
        
        # Cloud SQL connection name format: project:region:instance
        connection_name = f"{project_id}:{region}:{instance_name}"
        
        # URL format for Cloud SQL with Unix socket
        escaped_password = urllib.parse.quote_plus(password)
        return f"postgresql://{username}:{escaped_password}@/{database_name}?host=/cloudsql/{connection_name}"
    
    def _build_sqlite_url(self) -> str:
        """Build SQLite URL for development."""
        data_dir = os.environ.get('DATA_DIR', 
                                 os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.join(data_dir, 'api_keys.db')
        return f"sqlite:///{db_path}"
    
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine and session factory."""
        if self.database_url.startswith('sqlite'):
            # SQLite-specific configuration
            self.engine = create_engine(
                self.database_url,
                poolclass=StaticPool,
                connect_args={
                    "check_same_thread": False,
                    "timeout": 30
                },
                echo=os.environ.get('SQL_DEBUG', 'false').lower() == 'true'
            )
        else:
            # PostgreSQL configuration
            self.engine = create_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
                echo=os.environ.get('SQL_DEBUG', 'false').lower() == 'true'
            )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        logger.info(f"Database engine initialized with URL: {self._mask_password(self.database_url)}")
    
    def _mask_password(self, url: str) -> str:
        """Mask password in database URL for logging."""
        if '://' not in url:
            return url
        
        scheme, rest = url.split('://', 1)
        if '@' not in rest:
            return url
        
        auth, host_part = rest.split('@', 1)
        if ':' in auth:
            username, _ = auth.split(':', 1)
            return f"{scheme}://{username}:***@{host_part}"
        
        return url
    
    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def get_session(self):
        """Get a database session."""
        return self.SessionLocal()
    
    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            with self.engine.connect() as conn:
                if self.database_url.startswith('sqlite'):
                    result = conn.execute(text("SELECT 1"))
                else:
                    result = conn.execute(text("SELECT version()"))
                result.fetchone()
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information for health checks."""
        try:
            with self.engine.connect() as conn:
                if self.database_url.startswith('sqlite'):
                    result = conn.execute(text("SELECT sqlite_version()"))
                    version = result.fetchone()[0]
                    return {
                        'type': 'sqlite',
                        'version': version,
                        'status': 'healthy'
                    }
                else:
                    result = conn.execute(text("SELECT version()"))
                    version = result.fetchone()[0]
                    return {
                        'type': 'postgresql',
                        'version': version.split(' ')[1],  # Extract version number
                        'status': 'healthy'
                    }
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {
                'type': 'unknown',
                'version': 'unknown',
                'status': 'unhealthy',
                'error': str(e)
            }

# Global database manager instance
db_manager = DatabaseManager()

def get_database_session():
    """Dependency function to get database session for API endpoints."""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

def init_database():
    """Initialize database tables and connections."""
    db_manager.create_tables()
    
    # Test the connection
    if not db_manager.test_connection():
        raise RuntimeError("Failed to connect to database")
    
    logger.info("Database initialization completed successfully")

# For backward compatibility with existing code
def get_db_path() -> str:
    """Get database path (for SQLite) or connection info."""
    if db_manager.database_url.startswith('sqlite'):
        return db_manager.database_url.replace('sqlite:///', '')
    else:
        return db_manager.database_url