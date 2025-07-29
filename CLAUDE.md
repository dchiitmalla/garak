# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Garak is an LLM vulnerability scanner and red-teaming framework - a security testing tool for language models. It probes for hallucination, data leakage, prompt injection, misinformation, toxicity generation, jailbreaks, and other security weaknesses in LLMs.

## Development Commands

### Testing
```bash
python3 -m pytest                    # Run all tests
python3 -m pytest tests/            # Run specific test directory
python3 -m pytest -v                # Verbose test output
python3 -m pytest --cov=garak       # Run tests with coverage
```

### Code Quality
```bash
python3 -m black .                  # Format code (line length: 88)
python3 -m pylint garak/            # Lint the main package
python3 -m pylint tests/            # Lint test files
```

### Installation and Development Setup
```bash
# Development install
python3 -m pip install -e .

# Install with optional dependencies
python3 -m pip install -e .[tests,lint,calibration,audio]

# Run garak 
python3 -m garak --help
python3 -m garak --list_probes
python3 -m garak --list_generators

# Run specific tests
python3 -m pytest tests/probes/test_probes.py  # Test specific probe file
python3 -m pytest tests/detectors/            # Test detector directory
python3 -m pytest -k "test_name"              # Run tests matching pattern
```

## Architecture

### Core Components

1. **Probes** (`garak/probes/`) - Generate test interactions with LLMs to expose vulnerabilities
2. **Detectors** (`garak/detectors/`) - Analyze LLM outputs to identify failure modes  
3. **Generators** (`garak/generators/`) - Interface adapters for different LLM providers (OpenAI, HuggingFace, etc.)
4. **Harnesses** (`garak/harnesses/`) - Coordinate testing workflow between probes and detectors
5. **Evaluators** (`garak/evaluators/`) - Process and report assessment results
6. **Buffs** (`garak/buffs/`) - Transform prompts (encoding, paraphrasing, etc.)

### Plugin Architecture

Garak uses a plugin-based architecture where each component type has:
- Base classes in `base.py` files that define interfaces
- Plugin modules that inherit from base classes
- Automatic plugin discovery and loading via `_plugins.py`
- Plugin cache for performance optimization

Data flow: `Probe → Buff (optional) → Generator → Model → Detector → Evaluator → Report`

Plugin types: `("probes", "detectors", "generators", "harnesses", "buffs")`

### Configuration System

- Configuration hierarchy: plugin defaults < base config < site config < run config < CLI params
- YAML configuration files in `garak/configs/` (default.yaml, fast.yaml, broad.yaml, etc.)
- Runtime configuration managed via `_config.py`
- Plugin-specific configs loaded dynamically
- Environment variables: `OPENAI_API_KEY`, `HF_INFERENCE_TOKEN`, `REPLICATE_API_TOKEN`, etc.

### Data and Resources

- Static test data in `garak/data/` (payloads, test sets, etc.)
- Runtime resources in `garak/resources/` (attack implementations, utilities)
- Plugin cache for performance optimization

## Key Development Patterns

### Creating New Plugins

1. Inherit from appropriate base class (`base.Probe`, `base.Detector`, etc.)
2. Override minimal required methods (e.g., `_call_model` for generators)
3. Define `recommended_detectors` for probes
4. Place in appropriate module directory

Example plugin structure:
```python
class ExampleProbe(garak.probes.base.Probe):
    recommended_detector = ["always.Pass"]
    tags = ["avid-effect:security:S0403"]
    goal = "test specific vulnerability"
    prompts = ["test prompt here"]
```

### Testing Strategy

- Unit tests for individual plugins in `tests/[component]/`
- Integration tests that combine components
- Test generators use `test.Blank`, `test.Repeat`, and `test.Single` generators
- Test detectors use `always.Pass`, `always.Fail`, and `always.Random`
- Mock external dependencies (API calls, file systems)
- Use `conftest.py` files for shared test fixtures
- Test with: `python3 -m garak -m test.Blank -p mymodule -d always.Pass`

### Security Considerations

- All contributions must be for defensive security research
- Follow responsible disclosure for vulnerabilities
- Only include ethically appropriate test data
- Validate external inputs and API responses

## Important Files

- `garak/__main__.py` - CLI entry point
- `garak/cli.py` - Command line interface implementation  
- `garak/_plugins.py` - Plugin loading and discovery
- `garak/_config.py` - Configuration management
- `garak/attempt.py` - Core data structures for test attempts
- `garak/report.py` - Report generation and formatting
- `garak/interactive.py` - Interactive mode functionality
- `pyproject.toml` - Build configuration and dependencies

## Dashboard Component

The `dashboard/` directory contains a Flask web application for visualizing garak results with authentication, job management, and report analysis capabilities. It includes both a web UI and a comprehensive public API.

### Dashboard Development Commands
```bash
# Setup virtual environment (recommended)
cd dashboard && python3 -m venv venv && source venv/bin/activate

# Install dashboard dependencies
pip install -r requirements.txt

# Run dashboard locally (development)
export DISABLE_AUTH=true  # For development only
python app.py  # Starts on http://localhost:8000

# Run with production server
gunicorn --workers 2 --bind 0.0.0.0:8080 app:app

# Run with Docker
docker build -t garak-dashboard -f dashboard/Dockerfile .
docker run -p 8080:8080 garak-dashboard

# Build for GCP deployment (requires AMD64 architecture)
docker buildx build --platform linux/amd64 -f dashboard/Dockerfile -t gcr.io/PROJECT_ID/garak-dashboard:latest .

# Load Firebase environment (if configured)
source load_env.sh
```

### Dashboard Testing Commands
```bash
# Always use virtual environment for dashboard testing
cd dashboard && source venv/bin/activate

# Run all dashboard tests with custom test runner
python run_tests.py --all                    # All tests
python run_tests.py --unit                   # Unit tests only  
python run_tests.py --integration            # Integration tests only
python run_tests.py --coverage --html        # With coverage report

# Run standard pytest (alternative)  
cd dashboard && pytest tests/
pytest tests/unit/                           # Unit tests
pytest tests/integration/                    # Integration tests
pytest -m "not auth"                         # Skip auth tests (for DISABLE_AUTH=true)
pytest -v -k "test_scan"                     # Run tests matching pattern

# Test specific API endpoints locally
export DISABLE_AUTH=true
python app.py &
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/generators

# Test Pydantic models directly
python -c "from api.core.models import ErrorResponse; print(ErrorResponse(error='test', message='test').model_dump())"

# Check rate limiter functionality
python -c "from api.core.rate_limiter import RateLimiter; r = RateLimiter(); print(r.is_rate_limited('test', 10, 60))"
```

### Dashboard Architecture

The dashboard uses a modular Flask application structure with:
- **Web UI**: Flask templates for job management and result visualization
- **Authentication**: Firebase integration or bypass for development
- **Job Management**: Background task execution with status tracking
- **Report Processing**: HTML/JSON report parsing and analysis
- **Public API**: RESTful API with authentication and rate limiting

Key files:
- `app.py` - Main Flask application with job management logic
- `auth.py` - Firebase authentication integration
- `tasks.py` - Background job orchestration
- `html_report_parser.py` - Report parsing for BigQuery upload

## Public API System

The dashboard includes a comprehensive public API organized in a clean package structure for programmatic access to garak red-teaming functionality.

### API Package Structure
```
dashboard/api/
├── core/               # Core functionality
│   ├── auth.py        # API key authentication & management
│   ├── models.py      # Pydantic request/response models
│   ├── rate_limiter.py # Redis-based rate limiting
│   └── utils.py       # Shared utilities (eliminates circular deps)
├── v1/                # API version 1 endpoints
│   ├── scans.py       # Scan management (CRUD operations)
│   ├── metadata.py    # Discovery (generators, probes, models)
│   └── admin.py       # API key management, system stats
└── docs.py            # OpenAPI/Swagger documentation
```

### API Development Commands
```bash
# Use virtual environment
source venv/bin/activate

# Test API endpoints locally
curl -X GET http://localhost:8000/api/v1/info

# Create bootstrap admin API key (first time setup)
curl -X POST http://localhost:8000/api/v1/admin/bootstrap

# Test with Redis rate limiting (requires Redis)
export REDIS_URL=redis://localhost:6379/0
python app.py

# View API documentation
# http://localhost:8000/api/docs (Swagger UI)
# http://localhost:8000/api/docs/examples (Usage examples)

# Test API module imports
python3 -c "from api.v1.scans import api_v1; print('✓ API imports working')"
```

### API Architecture

- **Authentication**: API key-based with SQLite storage, SHA256 hashing
- **Rate Limiting**: Redis-based sliding window algorithm with per-key/per-endpoint limits
- **Validation**: Pydantic models for request/response validation with automatic OpenAPI generation
- **Documentation**: Interactive Swagger UI with usage examples
- **Modular Design**: Clean separation of concerns with shared utilities to eliminate circular dependencies

### Docker Deployment and Environment Issues

The dashboard includes Docker support for deployment to Cloud Run. Key considerations:

**Docker Build Commands**:
```bash
# Standard Docker build
docker build -f dashboard/Dockerfile -t garak-dashboard .

# Build for GCP (AMD64 required for Cloud Run)
docker buildx build --platform linux/amd64 -f dashboard/Dockerfile -t gcr.io/PROJECT_ID/garak-dashboard:latest .

# Test locally before deployment
docker run -d -p 8080:8080 -e PORT=8080 -e DISABLE_AUTH=true garak-dashboard
```

**Common Environment Issues**:
- Missing optional dependencies can cause garak plugin enumeration to fail
- NLTK data downloads need proper cache directory permissions  
- HuggingFace transformers require cache configuration
- Garak scans may timeout without proper resource limits (30min default timeout implemented)

**Environment Variables for Container**:
- `HF_HOME=/home/garak/.cache/huggingface` - HuggingFace model cache
- `NLTK_DATA=/usr/local/share/nltk_data:/home/garak/.nltk_data` - NLTK data paths
- `TORCH_HOME=/home/garak/.cache/torch` - PyTorch cache
- `DISABLE_AUTH=true` - Bypass authentication for development/testing

Key endpoints:
- `/api/v1/scans` - Scan management (create, list, get status, cancel, download reports)
- `/api/v1/generators` - Available model generators and supported models
- `/api/v1/probes` - Available security probe categories and individual probes  
- `/api/v1/admin/*` - API key management and system statistics (admin only)
- `/api/v1/info` - API capabilities and version information
- `/api/v1/health` - System health check with component status

### API Key Management Workflow
```bash
# 1. Bootstrap initial admin key (first time only)
POST /api/v1/admin/bootstrap
# Returns: {"api_key": "garak_...", "message": "Store securely"}

# 2. Create regular API keys (using admin key)
POST /api/v1/admin/api-keys
Headers: X-API-Key: garak_admin_key_here
{
  "name": "Scan API Key",
  "description": "For automated security scans",
  "permissions": ["read", "write"],
  "rate_limit": 100,
  "expires_days": 90
}

# 3. Use API key for scans
POST /api/v1/scans
Headers: X-API-Key: garak_scan_key_here
{
  "generator": "openai",
  "model_name": "gpt-3.5-turbo",
  "probe_categories": ["dan", "security"],
  "api_keys": {"openai_api_key": "sk-..."}
}

# 4. Monitor and manage keys
GET /api/v1/admin/api-keys              # List all keys
GET /api/v1/admin/api-keys/{id}/rate-limit  # Check rate limit status
DELETE /api/v1/admin/api-keys/{id}      # Delete key
```

## Dashboard Testing Infrastructure

The dashboard includes a comprehensive pytest-based testing system with 60+ tests covering all functionality:

### Test Organization
```
dashboard/tests/
├── conftest.py           # Shared fixtures and configuration
├── unit/                 # Unit tests (42+ tests)
│   ├── test_models.py    # Pydantic model validation tests
│   ├── test_utils.py     # Utility function tests
│   ├── test_rate_limiter.py # Rate limiting tests
│   ├── test_database.py  # Database model tests
│   └── test_probe_error_handling.py # Probe error handling tests
└── integration/          # Integration tests (38+ tests)
    ├── test_api_endpoints.py # API endpoint tests
    ├── test_auth.py      # Authentication tests
    └── test_job_error_handling.py # Job execution error handling tests
```

### Test Markers and Categories
- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, full stack)
- `@pytest.mark.auth` - Authentication-related tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.models` - Pydantic model tests

### Key Testing Patterns
- **Fixtures in conftest.py**: `app`, `client`, `api_models`, `utils`, `rate_limiter`
- **Test database isolation**: Each test uses temporary SQLite database
- **API endpoint testing**: Uses Flask test client with JSON requests/responses
- **Mock external dependencies**: Redis, Firebase, external APIs
- **Environment setup**: `DISABLE_AUTH=true` and `FLASK_ENV=testing` automatically configured

## Critical Job Execution and Error Handling

### Job Persistence and Recovery
The dashboard implements robust job persistence with automatic disk reload capabilities:
- Jobs are atomically written to disk using temporary files to prevent corruption
- Scan data can be retrieved even after server restarts or memory clearing
- Automatic fallback to disk-based loading when jobs aren't in memory
- Race condition prevention through file locking and validation

### Probe Error Handling
Recent improvements ensure jobs continue execution despite individual probe failures:
- **AutoDAN Compatibility**: AutoDAN probe gracefully handles non-HuggingFace generators by early detection and fallback
- **Logging Configuration**: HTTP client loggers (`httpcore`, `httpx`, `urllib3`) set to WARNING level to prevent recursive logging errors
- **Script-level Error Handling**: Bash execution scripts include error recovery and report validation
- **Atomic File Operations**: Job data uses atomic writes with `fsync` and temporary files

### Error Recovery Patterns
```python
# Probe compatibility checking example
if not isinstance(generator, Model):
    logging.warning(f"Probe skipped: requires HuggingFace models, got {type(generator).__name__}")
    return []  # Return empty instead of crashing

# Atomic file write pattern
temp_path = job_file_path + '.tmp'
with open(temp_path, 'w') as f:
    json.dump(job_data, f, indent=2)
    f.flush()
    os.fsync(f.fileno())
os.rename(temp_path, job_file_path)  # Atomic move
```

## Advanced Dashboard Features

### Scan Persistence Architecture
- **In-Memory Management**: Global `JOBS` dictionary for active scan tracking
- **Disk Persistence**: JSON files in `DATA_DIR` for permanent storage
- **Automatic Recovery**: Functions `_reload_jobs_from_disk()` and `_reload_specific_job()` for memory reconstruction
- **Data Validation**: Empty file detection, JSON validation, and field verification

### Background Job Management  
- **Threading Model**: Daemon threads for non-blocking scan execution
- **Status Tracking**: Real-time status updates with progress estimation
- **Timeout Handling**: 30-minute execution timeout with graceful cleanup
- **Process Management**: PID tracking and proper subprocess lifecycle management

### API Robustness Features
- **Rate Limiting**: Redis-based sliding window with per-endpoint limits
- **Request Validation**: Pydantic models with comprehensive error handling
- **Authentication**: SHA256-hashed API keys with role-based permissions
- **Error Recovery**: Automatic scan reload from disk when not in memory

## Development Workflow Considerations

### Testing Critical Systems
```bash
# Test probe error handling specifically
pytest tests/unit/test_probe_error_handling.py -v

# Test job persistence and recovery
pytest tests/integration/test_api_endpoints.py -k "persistence or retrieval" -v

# Test error handling under various conditions
pytest tests/integration/test_job_error_handling.py -v
```

### Common Debugging Scenarios
- **Empty Job Files**: Check for race conditions in job creation vs background execution
- **Logging Recursion**: Verify HTTP client logger levels are set to WARNING or higher
- **Probe Failures**: Check generator compatibility (especially AutoDAN with non-HF models)
- **Memory vs Disk Sync**: Use scan retrieval endpoints to test disk reload functionality

### Environment Variables for Troubleshooting
```bash
export GARAK_LOG_LEVEL=DEBUG      # Enable verbose garak logging
export PYTHONUNBUFFERED=1         # Prevent output buffering issues
export DISABLE_AUTH=true          # Bypass auth for local development
export REDIS_URL=redis://localhost:6379/0  # Enable rate limiting (optional)
```