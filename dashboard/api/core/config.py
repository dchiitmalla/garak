"""
Environment configuration management for Garak Dashboard API.

This module provides centralized configuration management supporting
development, staging, and production environments.
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    url: str
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False


@dataclass
class RedisConfig:
    """Redis configuration settings."""
    url: str
    max_connections: int = 10
    retry_on_timeout: bool = True
    socket_timeout: int = 5


@dataclass
class StorageConfig:
    """Storage configuration settings."""
    use_gcs: bool
    reports_bucket: Optional[str] = None
    job_data_bucket: Optional[str] = None
    local_reports_dir: str = "reports"
    local_data_dir: str = "data"


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    secret_key: str
    api_key_expiry_days: int = 365
    session_timeout: int = 3600
    max_api_keys_per_user: int = 10


@dataclass
class AppConfig:
    """Main application configuration."""
    environment: str
    debug: bool
    project_id: Optional[str]
    region: str
    port: int
    
    # Component configurations
    database: DatabaseConfig
    redis: RedisConfig
    storage: StorageConfig
    security: SecurityConfig
    
    # Feature flags
    enable_auth: bool = True
    enable_rate_limiting: bool = True
    enable_monitoring: bool = True


class ConfigManager:
    """Manages application configuration based on environment."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self.environment = os.environ.get('ENVIRONMENT', 'development')
        self.config = self._load_config()
        logger.info(f"Configuration loaded for environment: {self.environment}")
    
    def _load_config(self) -> AppConfig:
        """Load configuration based on environment."""
        # Base configuration
        base_config = self._get_base_config()
        
        # Environment-specific overrides
        if self.environment == 'production':
            return self._get_production_config(base_config)
        elif self.environment == 'staging':
            return self._get_staging_config(base_config)
        else:
            return self._get_development_config(base_config)
    
    def _get_base_config(self) -> Dict[str, Any]:
        """Get base configuration common to all environments."""
        return {
            'environment': self.environment,
            'project_id': os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('PROJECT_ID'),
            'region': os.environ.get('REGION', 'us-central1'),
            'port': int(os.environ.get('PORT', '8080')),
            'debug': os.environ.get('DEBUG', 'false').lower() == 'true',
        }
    
    def _get_development_config(self, base: Dict[str, Any]) -> AppConfig:
        """Get development environment configuration."""
        return AppConfig(
            environment=base['environment'],
            debug=True,
            project_id=base['project_id'],
            region=base['region'],
            port=base['port'],
            
            database=DatabaseConfig(
                url=self._get_database_url_dev(),
                pool_size=2,
                max_overflow=5,
                echo=base['debug']
            ),
            
            redis=RedisConfig(
                url=os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            ),
            
            storage=StorageConfig(
                use_gcs=False,
                local_reports_dir=os.environ.get('REPORT_DIR', 'reports'),
                local_data_dir=os.environ.get('DATA_DIR', 'data')
            ),
            
            security=SecurityConfig(
                secret_key=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
                api_key_expiry_days=30
            ),
            
            enable_auth=os.environ.get('DISABLE_AUTH', 'false').lower() != 'true',
            enable_rate_limiting=False,  # Disabled for development
            enable_monitoring=False
        )
    
    def _get_staging_config(self, base: Dict[str, Any]) -> AppConfig:
        """Get staging environment configuration."""
        return AppConfig(
            environment=base['environment'],
            debug=base['debug'],
            project_id=base['project_id'],
            region=base['region'],
            port=base['port'],
            
            database=DatabaseConfig(
                url=self._get_database_url_cloud(),
                pool_size=3,
                max_overflow=7,
                echo=False
            ),
            
            redis=RedisConfig(
                url=self._get_redis_url_cloud()
            ),
            
            storage=StorageConfig(
                use_gcs=True,
                reports_bucket=f"{base['project_id']}-garak-reports-staging",
                job_data_bucket=f"{base['project_id']}-garak-job-data-staging"
            ),
            
            security=SecurityConfig(
                secret_key=self._get_secret('garak-app-secret-key'),
                api_key_expiry_days=90
            ),
            
            enable_auth=True,
            enable_rate_limiting=True,
            enable_monitoring=True
        )
    
    def _get_production_config(self, base: Dict[str, Any]) -> AppConfig:
        """Get production environment configuration."""
        return AppConfig(
            environment=base['environment'],
            debug=False,
            project_id=base['project_id'],
            region=base['region'],
            port=base['port'],
            
            database=DatabaseConfig(
                url=self._get_database_url_cloud(),
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
                echo=False
            ),
            
            redis=RedisConfig(
                url=self._get_redis_url_cloud(),
                max_connections=20
            ),
            
            storage=StorageConfig(
                use_gcs=True,
                reports_bucket=f"{base['project_id']}-garak-reports",
                job_data_bucket=f"{base['project_id']}-garak-job-data"
            ),
            
            security=SecurityConfig(
                secret_key=self._get_secret('garak-app-secret-key'),
                api_key_expiry_days=365,
                max_api_keys_per_user=20
            ),
            
            enable_auth=True,
            enable_rate_limiting=True,
            enable_monitoring=True
        )
    
    def _get_database_url_dev(self) -> str:
        """Get database URL for development (SQLite)."""
        if url := os.environ.get('DATABASE_URL'):
            return url
        
        data_dir = Path(os.environ.get('DATA_DIR', 'data'))
        data_dir.mkdir(exist_ok=True)
        return f"sqlite:///{data_dir}/garak_dashboard.db"
    
    def _get_database_url_cloud(self) -> str:
        """Get database URL for cloud deployment (PostgreSQL)."""
        if url := os.environ.get('DATABASE_URL'):
            return url
        
        # Build Cloud SQL connection URL
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('PROJECT_ID')
        region = os.environ.get('CLOUD_SQL_REGION', 'us-central1')
        instance = os.environ.get('CLOUD_SQL_INSTANCE', 'garak-dashboard-db')
        database = os.environ.get('CLOUD_SQL_DATABASE', 'garak_dashboard')
        username = os.environ.get('CLOUD_SQL_USERNAME', 'garak_user')
        password = os.environ.get('CLOUD_SQL_PASSWORD') or self._get_secret('garak-db-password')
        
        connection_name = f"{project_id}:{region}:{instance}"
        return f"postgresql://{username}:{password}@/{database}?host=/cloudsql/{connection_name}"
    
    def _get_redis_url_cloud(self) -> str:
        """Get Redis URL for cloud deployment."""
        if url := os.environ.get('REDIS_URL'):
            return url
        
        host = os.environ.get('REDIS_HOST', 'localhost')
        port = os.environ.get('REDIS_PORT', '6379')
        db = os.environ.get('REDIS_DB', '0')
        
        return f"redis://{host}:{port}/{db}"
    
    def _get_secret(self, secret_name: str) -> str:
        """Get secret from Google Secret Manager or environment."""
        # First try environment variable
        env_value = os.environ.get(secret_name.upper().replace('-', '_'))
        if env_value:
            return env_value
        
        # Try Google Secret Manager in cloud environments
        if self.environment in ['staging', 'production']:
            try:
                from google.cloud import secretmanager
                client = secretmanager.SecretManagerServiceClient()
                project_id = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('PROJECT_ID')
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": name})
                return response.payload.data.decode("UTF-8")
            except Exception as e:
                logger.error(f"Failed to get secret {secret_name}: {e}")
        
        # Fallback to default
        return f"default-{secret_name}"
    
    def get_config(self) -> AppConfig:
        """Get the current configuration."""
        return self.config
    
    def get_flask_config(self) -> Dict[str, Any]:
        """Get Flask-specific configuration."""
        return {
            'DEBUG': self.config.debug,
            'SECRET_KEY': self.config.security.secret_key,
            'JSONIFY_PRETTYPRINT_REGULAR': self.config.debug,
            'JSON_SORT_KEYS': False,
        }
    
    def setup_logging(self):
        """Set up logging configuration."""
        log_level = logging.DEBUG if self.config.debug else logging.INFO
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Set specific loggers
        loggers = {
            'sqlalchemy.engine': logging.WARNING,
            'sqlalchemy.pool': logging.WARNING,
            'google.cloud': logging.WARNING,
            'urllib3': logging.WARNING,
        }
        
        for logger_name, level in loggers.items():
            logging.getLogger(logger_name).setLevel(level)
        
        logger.info(f"Logging configured for {self.config.environment} environment")


# Global configuration manager
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """Get the current application configuration."""
    return config_manager.get_config()


def get_flask_config() -> Dict[str, Any]:
    """Get Flask-specific configuration."""
    return config_manager.get_flask_config()


def setup_logging():
    """Set up application logging."""
    config_manager.setup_logging()