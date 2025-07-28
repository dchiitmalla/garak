# Garak Dashboard API Architecture

## Overview

The Garak Dashboard API provides programmatic access to the Garak LLM vulnerability scanner, enabling developers to integrate security testing capabilities into their workflows. The API is built with Flask and follows RESTful principles with comprehensive authentication, rate limiting, and documentation.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                       │
├─────────────────────────────────────────────────────────────┤
│                    HTTP/HTTPS Layer                         │
├─────────────────────────────────────────────────────────────┤
│                    Flask Application                        │
│  ┌─────────────────┬─────────────────┬─────────────────┐   │
│  │   Web UI        │   Public API    │   Admin API     │   │
│  │   (Templates)   │   (v1)          │   (Admin Only)  │   │
│  └─────────────────┴─────────────────┴─────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                 Core Services Layer                         │
│  ┌─────────────────┬─────────────────┬─────────────────┐   │
│  │ Authentication  │  Rate Limiting  │  Job Management │   │
│  │    (SQLite)     │    (Redis)      │  (Background)   │   │
│  └─────────────────┴─────────────────┴─────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    Data Storage                             │
│  ┌─────────────────┬─────────────────┬─────────────────┐   │
│  │   API Keys DB   │   Job Data      │   Reports       │   │
│  │   (SQLite)      │   (JSON Files)  │   (Files)       │   │
│  └─────────────────┴─────────────────┴─────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                 External Dependencies                       │
│  ┌─────────────────┬─────────────────┬─────────────────┐   │
│  │   Garak Core    │   LLM APIs      │   Firebase      │   │
│  │   (Scanner)     │   (OpenAI, etc) │   (Optional)    │   │
│  └─────────────────┴─────────────────┴─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Package Structure

### Core Architecture Principles

1. **Separation of Concerns**: Each module has a single responsibility
2. **Dependency Inversion**: High-level modules don't depend on low-level modules
3. **Elimination of Circular Dependencies**: Shared utilities prevent import cycles
4. **Version Isolation**: API versions are isolated for backward compatibility

### Package Organization

```
dashboard/api/
├── __init__.py                 # Package exports and version info
├── core/                       # Core functionality (reusable)
│   ├── __init__.py            # Core module exports
│   ├── auth.py                # Authentication & authorization
│   ├── models.py              # Pydantic data models
│   ├── rate_limiter.py        # Rate limiting implementation
│   └── utils.py               # Shared utilities
├── v1/                        # API version 1 (extensible for v2, v3...)
│   ├── __init__.py           # V1 module exports
│   ├── scans.py              # Scan lifecycle management
│   ├── metadata.py           # Discovery endpoints
│   └── admin.py              # Administrative operations
└── docs.py                   # API documentation (OpenAPI/Swagger)
```

## Core Components

### 1. Authentication System (`api/core/auth.py`)

**Purpose**: Secure API access using API key-based authentication with role-based permissions.

**Architecture**:
```python
┌─────────────────────────────────────────────────────────┐
│                APIKeyManager                            │
├─────────────────────────────────────────────────────────┤
│ + generate_api_key()     # Creates new API keys         │
│ + validate_api_key()     # Validates incoming requests  │
│ + list_api_keys()        # Lists all keys (admin)       │
│ + revoke_api_key()       # Deactivates keys            │
│ + delete_api_key()       # Permanently removes keys     │
└─────────────────────────────────────────────────────────┘
```

**Key Features**:
- **SQLite Storage**: Lightweight, file-based database for API key metadata
- **SHA256 Hashing**: Secure key storage (only hash stored, not plaintext)
- **Role-Based Access**: Read, write, and admin permission levels
- **Expiration Support**: Configurable key expiration dates
- **Usage Tracking**: Request count and last-used timestamps

**Security Model**:
```
API Key Format: garak_{32_random_bytes_base64}
Storage: SHA256(api_key) → {metadata}
Headers: Authorization: Bearer {api_key} OR X-API-Key: {api_key}
```

**Database Schema**:
```sql
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_hash TEXT UNIQUE NOT NULL,
    key_prefix TEXT NOT NULL,           -- First 8 chars for identification
    name TEXT,                          -- Human-readable name
    description TEXT,
    permissions TEXT DEFAULT 'read,write', -- Comma-separated permissions
    rate_limit INTEGER DEFAULT 100,        -- Requests per minute
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    usage_count INTEGER DEFAULT 0
);
```

### 2. Rate Limiting (`api/core/rate_limiter.py`)

**Purpose**: Prevent API abuse and ensure fair resource allocation using Redis-based sliding window algorithm.

**Architecture**:
```python
┌─────────────────────────────────────────────────────────┐
│                RateLimiter                              │
├─────────────────────────────────────────────────────────┤
│ + is_rate_limited()      # Check if request allowed     │
│ + get_rate_info()        # Get current usage stats      │
│ + @rate_limit()          # Decorator for endpoints      │
└─────────────────────────────────────────────────────────┘
```

**Sliding Window Algorithm**:
```
Redis Key: rate_limit:{scope}:{identifier}
Data Structure: Sorted Set (ZSET)
Score: timestamp, Member: unique_request_id

Window Logic:
1. Remove expired entries (older than window)
2. Count current requests in window
3. Add new request if under limit
4. Return rate limit status
```

**Rate Limit Scopes**:
- **Global**: `rate_limit:global` - Shared across all users
- **Per API Key**: `rate_limit:key:{key_id}` - Per API key across all endpoints
- **Per Endpoint**: `rate_limit:key:{key_id}:endpoint:{method}:{endpoint}` - Granular control
- **IP-based**: `rate_limit:ip:{client_ip}` - For unauthenticated requests

**Headers**:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1673123456
X-RateLimit-Window: 60
```

### 3. Data Models (`api/core/models.py`)

**Purpose**: Type-safe request/response validation using Pydantic with automatic OpenAPI schema generation.

**Model Categories**:

1. **Request Models**: Validate incoming data
   ```python
   class CreateScanRequest(BaseModel):
       generator: str
       model_name: str
       probe_categories: Optional[List[str]] = None
       probes: Optional[List[str]] = None
       api_keys: Optional[Dict[str, str]] = None
   ```

2. **Response Models**: Structure outgoing data
   ```python
   class ScanMetadata(BaseModel):
       scan_id: str
       status: ScanStatus
       created_at: datetime
       progress: Optional[ScanProgressInfo] = None
   ```

3. **Error Models**: Consistent error responses
   ```python
   class ErrorResponse(BaseModel):
       error: str
       message: str
       details: Optional[Any] = None
       timestamp: datetime = Field(default_factory=datetime.now)
   ```

**Benefits**:
- **Automatic Validation**: Invalid requests rejected with detailed errors
- **OpenAPI Generation**: Schema automatically generated for documentation
- **Type Safety**: IDE support and runtime type checking
- **Serialization**: Automatic JSON conversion

### 4. Shared Utilities (`api/core/utils.py`)

**Purpose**: Eliminate circular dependencies and provide shared functionality across API modules.

**Key Functions**:

1. **App Integration**:
   ```python
   def get_jobs_data() -> Dict[str, Any]
   def get_probe_categories() -> Dict[str, List[str]]
   def get_generators() -> Dict[str, str]
   def run_garak_job_wrapper(job_id, generator, model_name, ...)
   ```

2. **Request Validation**:
   ```python
   def validate_json_request(model_class):
       """Decorator for Pydantic validation"""
   ```

3. **Error Handling**:
   ```python
   def create_error_handler(blueprint_name: str):
       """Standardized error handling"""
   ```

4. **Metadata Enhancement**:
   ```python
   GENERATOR_INFO = {
       'openai': {
           'display_name': 'OpenAI',
           'supported_models': ['gpt-4', 'gpt-3.5-turbo', ...],
           'requires_api_key': True
       }
   }
   ```

## API Endpoints

### 1. Scan Management (`api/v1/scans.py`)

**Purpose**: Core functionality for managing security scans throughout their lifecycle.

**Endpoints**:

| Method | Endpoint | Purpose | Auth | Rate Limit |
|--------|----------|---------|------|------------|
| POST | `/api/v1/scans` | Create new scan | Write | 10/min |
| GET | `/api/v1/scans` | List all scans | Read | 100/min |
| GET | `/api/v1/scans/{id}` | Get scan details | Read | 200/min |
| GET | `/api/v1/scans/{id}/status` | Get scan status | Read | 200/min |
| GET | `/api/v1/scans/{id}/progress` | Get scan progress | Read | 100/min |
| DELETE | `/api/v1/scans/{id}` | Cancel scan | Write | 50/min |
| GET | `/api/v1/scans/{id}/reports/{type}` | Download reports | Read | 50/min |

**Scan Lifecycle**:
```
pending → running → completed
    ↓       ↓         ↓
cancelled   failed    (reports available)
```

**Integration with Garak Core**:
```python
# Background job execution
def run_garak_job(job_id, generator, model_name, probes, api_keys):
    """Execute garak scan in background thread"""
    # 1. Validate parameters against available generators/probes
    # 2. Create job configuration
    # 3. Execute garak CLI with parameters
    # 4. Monitor progress and update status
    # 5. Generate reports when complete
```

### 2. Discovery Endpoints (`api/v1/metadata.py`)

**Purpose**: Enable clients to discover available capabilities before creating scans.

**Endpoints**:

| Method | Endpoint | Purpose | Response |
|--------|----------|---------|----------|
| GET | `/api/v1/generators` | List all generators | Generator info with models |
| GET | `/api/v1/generators/{name}/models` | Models for generator | Model list |
| GET | `/api/v1/probes` | List probe categories | Categories with probes |
| GET | `/api/v1/probes/{category}` | Probes in category | Probe details |
| GET | `/api/v1/info` | API capabilities | Version, features |
| GET | `/api/v1/health` | System health | Component status |

**Dynamic Discovery**:
```python
# Generators loaded from garak core
GENERATORS = {
    'openai': 'OpenAI',
    'anthropic': 'Anthropic',
    'huggingface': 'HuggingFace',
    # ... discovered at runtime
}

# Probes organized by category
PROBE_CATEGORIES = {
    'dan': ['dan.Dan_11_0', 'dan.Dan_6_0', ...],
    'security': ['promptinject.HijackKillHumans', ...],
    # ... loaded from garak plugins
}
```

### 3. Administrative Operations (`api/v1/admin.py`)

**Purpose**: System administration and API key management for privileged users.

**Endpoints**:

| Method | Endpoint | Purpose | Auth Level |
|--------|----------|---------|------------|
| POST | `/api/v1/admin/bootstrap` | Create first admin key | None (one-time) |
| POST | `/api/v1/admin/api-keys` | Create API key | Admin |
| GET | `/api/v1/admin/api-keys` | List all keys | Admin |
| GET | `/api/v1/admin/api-keys/{id}` | Get key details | Admin |
| DELETE | `/api/v1/admin/api-keys/{id}` | Delete key | Admin |
| POST | `/api/v1/admin/api-keys/{id}/revoke` | Revoke key | Admin |
| GET | `/api/v1/admin/api-keys/{id}/rate-limit` | Rate limit status | Admin |
| GET | `/api/v1/admin/stats` | System statistics | Admin |

**Security Considerations**:
- **Bootstrap Protection**: Only allows admin creation if no admin keys exist
- **Admin Verification**: All admin endpoints require admin-level API key
- **Audit Logging**: All administrative actions logged with API key context
- **Key Isolation**: Users cannot access other users' keys

## Data Flow

### 1. Scan Creation Flow

```
Client Request
    ↓
Authentication Middleware (validate API key)
    ↓
Rate Limiting Middleware (check limits)
    ↓
Request Validation (Pydantic models)
    ↓
Scan Parameters Validation (generators/probes exist)
    ↓
Job Creation (UUID, metadata, status=pending)
    ↓
Background Thread Spawn (garak execution)
    ↓
Response to Client (scan_id, metadata)
    ↓
Background Processing (status updates)
    ↓
Report Generation (when complete)
```

### 2. Authentication Flow

```
API Request with Key
    ↓
Extract Key (Authorization header or X-API-Key)
    ↓
Hash Key (SHA256)
    ↓
Database Lookup (find key metadata)
    ↓
Validation Checks:
    - Key exists and is active
    - Not expired
    - Has required permissions
    ↓
Rate Limit Check (per key/endpoint)
    ↓
Request Processing
    ↓
Usage Tracking Update (increment count, update last_used)
```

### 3. Background Job Processing

```
Garak Job Thread
    ↓
Job Configuration Setup
    ↓
Environment Preparation (API keys, paths)
    ↓
Garak CLI Execution
    ↓
Progress Monitoring (status updates)
    ↓
Output Capture (logs, reports)
    ↓
Completion Handling:
    - Status update (completed/failed)
    - Report file organization
    - Cleanup temporary files
```

## Error Handling

### Error Response Format

All errors follow a consistent structure:
```json
{
    "error": "error_type",
    "message": "Human-readable description",
    "details": {...},  // Optional additional context
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Categories

1. **Authentication Errors** (401):
   - `api_key_required`: Missing API key
   - `invalid_api_key`: Key not found or invalid
   - `key_expired`: Key has expired
   - `insufficient_permissions`: Lacks required permission level

2. **Rate Limiting Errors** (429):
   - `rate_limit_exceeded`: Too many requests in time window

3. **Validation Errors** (400):
   - `validation_error`: Pydantic validation failed
   - `invalid_generator`: Unknown generator specified
   - `invalid_probe`: Unknown probe specified

4. **Resource Errors** (404):
   - `scan_not_found`: Scan ID doesn't exist
   - `report_not_found`: Report file doesn't exist

5. **System Errors** (500):
   - `internal_server_error`: Unexpected system error
   - `job_execution_failed`: Garak execution failed

## Security Considerations

### 1. API Key Security

- **Never Store Plaintext**: Only SHA256 hashes stored in database
- **Secure Generation**: Cryptographically secure random generation
- **Key Rotation**: Support for key expiration and renewal
- **Prefix Identification**: First 8 characters for user identification (non-sensitive)

### 2. Input Validation

- **Strict Validation**: All inputs validated against Pydantic schemas
- **Injection Prevention**: SQL injection protected by parameterized queries
- **File Path Validation**: Report downloads validate paths to prevent directory traversal

### 3. Rate Limiting

- **DDoS Protection**: Prevents abuse through rate limiting
- **Resource Management**: Ensures fair access to computational resources
- **Graduated Limits**: Different limits for different operations

### 4. Audit and Monitoring

- **Request Logging**: All API requests logged with key context
- **Admin Action Logging**: Administrative operations tracked
- **Health Monitoring**: System health endpoints for monitoring
- **Error Tracking**: Comprehensive error logging

## Configuration

### Environment Variables

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `REDIS_URL` | Redis connection for rate limiting | `redis://localhost:6379/0` | No |
| `DATA_DIR` | Directory for job data | `dashboard/data` | No |
| `REPORT_DIR` | Directory for reports | `dashboard/reports` | No |
| `DISABLE_AUTH` | Bypass authentication (dev only) | `false` | No |
| `DEBUG` | Enable debug logging | `false` | No |

### Database Configuration

**SQLite Settings**:
- **Location**: `{DATA_DIR}/api_keys.db`
- **Connection Pool**: Single connection (SQLite limitation)
- **Backup**: File-based, can be copied for backup
- **Migration**: Automatic table creation on startup

**Redis Settings**:
- **Purpose**: Rate limiting storage only
- **Fallback**: If Redis unavailable, rate limiting disabled (logs warning)
- **Data Expiration**: Keys auto-expire after 2x rate limit window

## Performance Considerations

### 1. Scalability

**Current Limitations**:
- SQLite: Single-writer limitation for API keys
- File-based job storage: No clustering support
- In-memory job status: Lost on restart

**Scale-out Options**:
- **Database**: Migrate to PostgreSQL/MySQL for multi-instance support
- **Job Storage**: Use Redis/database for job state
- **Load Balancing**: Sticky sessions required with current architecture

### 2. Optimization

**Request Processing**:
- **Connection Pooling**: Redis connection reuse
- **Caching**: Generator/probe metadata cached in memory
- **Validation**: Pydantic models compiled for performance

**Background Jobs**:
- **Threading**: Non-blocking job execution
- **Resource Limits**: Job concurrency controlled
- **Cleanup**: Automatic cleanup of completed jobs

## Future Architecture Considerations

### 1. Microservices Migration

```
Current Monolith:
Flask App (Web UI + API + Job Management)

Future Microservices:
├── API Gateway (routing, auth, rate limiting)
├── Scan Service (job management)
├── Report Service (report generation/storage)
└── Admin Service (key management)
```

### 2. Database Evolution

```
Current: SQLite + File Storage + Redis

Phase 1: PostgreSQL + File Storage + Redis
Phase 2: PostgreSQL + Object Storage + Redis
Phase 3: PostgreSQL + Object Storage + Redis Cluster
```

### 3. API Versioning Strategy

```
Current: /api/v1/*

Future:
├── /api/v1/* (legacy, maintained)
├── /api/v2/* (enhanced features)
└── /api/v3/* (breaking changes)

Version Support:
- v1: Maintained for 12 months after v2 release
- v2: Maintained for 12 months after v3 release
- Deprecation warnings in headers
```

## Monitoring and Observability

### 1. Health Checks

**System Health** (`/api/v1/health`):
- Redis connectivity
- Database accessibility
- Job system functionality
- Disk space availability

**Service Health**:
- Response time monitoring
- Error rate tracking
- API key usage patterns
- Rate limit hit rates

### 2. Metrics

**API Metrics**:
- Request count by endpoint
- Response time percentiles
- Error rates by error type
- Authentication success/failure rates

**Business Metrics**:
- Scans created per day
- API key usage distribution
- Most popular generators/probes
- Job completion rates

### 3. Logging

**Structured Logging**:
```json
{
    "timestamp": "2024-01-15T10:30:00Z",
    "level": "INFO",
    "component": "api_v1",
    "endpoint": "/api/v1/scans",
    "method": "POST",
    "api_key_id": 123,
    "scan_id": "uuid-here",
    "duration_ms": 150,
    "status_code": 201
}
```

## Conclusion

The Garak Dashboard API architecture provides a robust, scalable foundation for programmatic access to LLM security testing capabilities. The modular design supports future evolution while maintaining clean separation of concerns and strong security practices.

Key architectural strengths:
- **Modular Design**: Clean package organization supports maintenance and extension
- **Security First**: Comprehensive authentication, authorization, and rate limiting
- **Type Safety**: Pydantic models ensure data integrity and automatic documentation
- **Scalability**: Architecture supports future migration to microservices
- **Observability**: Built-in monitoring and logging capabilities

The architecture successfully eliminates circular dependencies, provides clear upgrade paths, and maintains high security standards while remaining developer-friendly through comprehensive documentation and consistent patterns.